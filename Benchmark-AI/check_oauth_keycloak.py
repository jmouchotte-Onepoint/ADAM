import json
import os
import secrets
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from run import BENCH, CHANGELOG, FIXTURE, sql_files


IMAGE = os.environ.get("ADAM_OAUTH_IMAGE", "adam-oauth-validation:local")
KEYCLOAK = (
    "quay.io/keycloak/keycloak:26.5.0@"
    "sha256:5fdd7cda82e58775ed124294c7e16fabc33166d38dfc4aabebda7d64e7a964bf"
)
ISSUER = "https://localhost:8443/realms/adam"
AUDIENCE = "https://postgres.example/"
USERS = {
    "nurse": ("00000000-0000-0000-0000-000000000001", "tenantA", "nurse"),
    "doctor": ("00000000-0000-0000-0000-000000000002", "tenantA", "doctor"),
    "wrong-tenant": ("00000000-0000-0000-0000-000000000003", "tenantB", "nurse"),
    "missing-profession": ("00000000-0000-0000-0000-000000000004", "tenantA", None),
    "other-subject": ("00000000-0000-0000-0000-000000000005", "tenantA", "nurse"),
    "missing-tenant": ("00000000-0000-0000-0000-000000000007", None, "nurse"),
    "unmapped": ("00000000-0000-0000-0000-000000000006", "tenantA", "nurse"),
}


def docker(*args: str, input_text: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["docker", *args], input=input_text, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if check and result.returncode:
        raise RuntimeError(f"Docker command failed: {result.stderr}")
    return result


def realm(name: str, password: str) -> dict:
    def claim_mapper(name: str) -> dict:
        return {
            "name": name, "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "config": {
                "user.attribute": name, "claim.name": name,
                "jsonType.label": "String", "access.token.claim": "true",
                "id.token.claim": "false", "userinfo.token.claim": "false",
            },
        }

    def client(name: str, audience: str) -> dict:
        return {
            "clientId": name, "enabled": True, "publicClient": True,
            "standardFlowEnabled": False, "directAccessGrantsEnabled": True,
            "serviceAccountsEnabled": False, "fullScopeAllowed": False,
            "consentRequired": False, "protocol": "openid-connect",
            "attributes": {"access.token.header.type.rfc9068": "true"},
            "defaultClientScopes": [], "optionalClientScopes": ["connect:postgres"],
            "protocolMappers": [
                {
                    "name": "audience", "protocol": "openid-connect",
                    "protocolMapper": "oidc-audience-mapper",
                    "config": {
                        "included.custom.audience": audience,
                        "access.token.claim": "true", "id.token.claim": "false",
                    },
                },
                {
                    "name": "subject", "protocol": "openid-connect",
                    "protocolMapper": "oidc-sub-mapper",
                    "config": {
                        "access.token.claim": "true", "id.token.claim": "false",
                        "userinfo.token.claim": "false",
                    },
                },
                claim_mapper("tenant_id"), claim_mapper("profession"),
            ],
        }

    return {
        "realm": name, "enabled": True, "sslRequired": "external",
        "accessTokenLifespan": 30,
        "clients": [client("postgres-test", AUDIENCE), client("wrong-audience", "https://other.invalid/")],
        "clientScopes": [{
            "name": "connect:postgres", "protocol": "openid-connect",
            "attributes": {"include.in.token.scope": "true"},
        }],
        "users": [
            {
                "id": subject if name == "adam" else str(uuid.UUID(int=uuid.UUID(subject).int + 100)),
                "username": username, "enabled": True,
                "firstName": "Synthetic", "lastName": username,
                "email": f"{username}@example.invalid", "emailVerified": True,
                "attributes": {
                    **({"tenant_id": [tenant]} if tenant else {}),
                    **({"profession": [profession]} if profession else {}),
                },
                "credentials": [{"type": "password", "value": password, "temporary": False}],
            }
            for username, (subject, tenant, profession) in USERS.items()
        ],
    }


def main() -> None:
    suffix = uuid.uuid4().hex[:12]
    keycloak = "adam-oauth-keycloak-" + suffix
    postgres = "adam-oauth-postgres-" + suffix
    certs = "adam-oauth-certs-" + suffix
    password = secrets.token_urlsafe(24)
    created = []
    volume_created = False
    try:
        with tempfile.TemporaryDirectory(prefix="adam-oauth-") as temporary:
            directory = Path(temporary)
            config = directory / "config"
            imports = directory / "imports"
            config.mkdir(mode=0o755)
            imports.mkdir(mode=0o755)
            for name in ("adam", "other"):
                path = imports / f"{name}-realm.json"
                path.write_text(json.dumps(realm(name, password)))
                path.chmod(0o644)
            (config / "postgresql.conf").write_text(
                "listen_addresses = '127.0.0.1'\n"
                "hba_file = '/config/pg_hba.conf'\nident_file = '/config/pg_ident.conf'\n"
                "oauth_validator_libraries = 'pg_oauth_validator'\n"
                f"pg_oauth_validator.audiences = '{AUDIENCE}'\n"
                "pg_oauth_validator.ca_file = '/certs/ca.crt'\n"
                "pg_oauth_validator.clock_skew = 0\n"
                "log_min_messages = debug1\n"
                "ssl = on\nssl_cert_file = '/certs/postgres.crt'\n"
                "ssl_key_file = '/certs/postgres.key'\n"
            )
            rule = (
                "hostssl validation read_validation {address} oauth "
                f'issuer="{ISSUER}" scope="connect:postgres" '
                "validator=pg_oauth_validator map=adam\n"
            )
            (config / "pg_hba.conf").write_text(
                "local all postgres trust\nlocal all all reject\n"
                + rule.format(address="127.0.0.1/32")
                + rule.format(address="::1/128")
                + "host all all all reject\n"
            )
            (config / "pg_ident.conf").write_text(
                "".join(f"adam {subject} read_validation\n" for subject, _, _ in list(USERS.values())[:-1])
                + "adam 00000000-0000-0000-0000-000000000065 read_validation\n"
            )
            docker("volume", "create", certs)
            volume_created = True
            certificate_script = """
set -eu
umask 077
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=adam-test-ca \
  -addext basicConstraints=critical,CA:TRUE \
  -addext keyUsage=critical,keyCertSign,cRLSign \
  -keyout /certs/ca.key -out /certs/ca.crt >/dev/null 2>&1
for name in postgres keycloak; do
  openssl req -new -newkey rsa:2048 -nodes -subj /CN=localhost \
    -addext subjectAltName=DNS:localhost -addext basicConstraints=critical,CA:FALSE \
    -addext keyUsage=critical,digitalSignature,keyEncipherment \
    -addext extendedKeyUsage=serverAuth -keyout /certs/$name.key \
    -out /certs/$name.csr >/dev/null 2>&1
  openssl x509 -req -days 1 -in /certs/$name.csr -CA /certs/ca.crt \
    -CAkey /certs/ca.key -CAcreateserial -copy_extensions copy \
    -out /certs/$name.crt >/dev/null 2>&1
done
chown postgres:postgres /certs/postgres.key
chown 1000:0 /certs/keycloak.key
chmod 600 /certs/postgres.key /certs/keycloak.key
chmod 644 /certs/ca.crt /certs/postgres.crt /certs/keycloak.crt
"""
            docker("run", "--rm", "--network=none", "--mount", f"type=volume,src={certs},dst=/certs",
                   "--entrypoint", "/bin/sh", IMAGE, "-c", certificate_script)
            docker(
                "run", "--detach", "--name", keycloak, "--memory=1g", "--cpus=2",
                "--publish", "127.0.0.1::8443",
                "--mount", f"type=volume,src={certs},dst=/certs,readonly",
                "--mount", f"type=bind,src={imports},dst=/opt/keycloak/data/import,readonly",
                KEYCLOAK, "start-dev", "--import-realm", "--hostname=https://localhost:8443",
                "--https-certificate-file=/certs/keycloak.crt",
                "--https-certificate-key-file=/certs/keycloak.key",
            )
            created.append(keycloak)
            port = docker("port", keycloak, "8443/tcp").stdout.strip().rsplit(":", 1)[1]
            docker("cp", f"{keycloak}:/certs/ca.crt", str(directory / "ca.crt"))
            context = ssl.create_default_context(cafile=str(directory / "ca.crt"))
            token_url = f"https://localhost:{port}/realms/{{realm}}/protocol/openid-connect/token"

            def token(username: str, *, realm_name: str = "adam",
                      client_id: str = "postgres-test", scope: str = "connect:postgres") -> str:
                body = urllib.parse.urlencode({
                    "grant_type": "password", "client_id": client_id,
                    "username": username, "password": password, "scope": scope,
                }).encode()
                request = urllib.request.Request(
                    token_url.format(realm=realm_name), data=body,
                    headers={"Host": "localhost:8443"},
                )
                with urllib.request.urlopen(request, context=context, timeout=5) as response:
                    return json.load(response)["access_token"]

            deadline = time.monotonic() + 180
            while True:
                try:
                    token("nurse")
                    break
                except urllib.error.HTTPError as error:
                    if error.code not in (404, 503):
                        details = json.load(error)
                        raise RuntimeError(
                            f"Keycloak token endpoint returned HTTP {error.code}: "
                            f"{details.get('error')} / {details.get('error_description')}"
                        ) from error
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Keycloak did not become ready") from error
                    time.sleep(2)
                except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                    if isinstance(error, urllib.error.URLError) and isinstance(error.reason, ssl.SSLCertVerificationError):
                        raise RuntimeError("Keycloak TLS validation failed") from error
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Keycloak did not become ready")
                    state = docker("inspect", "-f", "{{.State.Running}}", keycloak).stdout.strip()
                    if state != "true":
                        raise RuntimeError("Keycloak exited before becoming ready")
                    time.sleep(2)
            docker(
                "run", "--detach", "--name", postgres, "--network", f"container:{keycloak}",
                "--memory=1g", "--cpus=1", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
                "--env", "POSTGRES_DB=validation",
                "--mount", f"type=volume,src={certs},dst=/certs,readonly",
                "--mount", f"type=bind,src={config},dst=/config,readonly",
                "--mount", f"type=bind,src={BENCH / 'oauth/oauth_claim_client.c'},dst=/tmp/client.c,readonly",
                IMAGE, "postgres", "-c", "config_file=/config/postgresql.conf",
            )
            created.append(postgres)
            deadline = time.monotonic() + 90
            while docker("exec", postgres, "pg_isready", "-h", "127.0.0.1", check=False).returncode:
                if time.monotonic() >= deadline:
                    raise TimeoutError("PostgreSQL did not become ready")
                time.sleep(1)
            docker("exec", postgres, "cc", "-Wall", "-Wextra", "-Werror",
                   "-I/usr/include/postgresql", "/tmp/client.c", "-o", "/tmp/client",
                   "-L/usr/local/lib", "-ljansson", "-lpq", "-lcrypto")

            sql = ["BEGIN; CREATE SCHEMA adam; SET search_path TO adam, public;"]
            sql.extend(path.read_text() for path in sql_files(CHANGELOG))
            sql.append((FIXTURE).read_text())
            sql.append("""
INSERT INTO parcours.etapes(id, tenant_id) VALUES ('parcours-oauth', 'tenantA');
INSERT INTO protected_records(id, tenant_id) VALUES ('parcours-oauth', 'tenantA');
INSERT INTO relations(user_type,user_id,relation,object_type,object_id,tenant_id)
SELECT 'users', subject, 'assigned', 'etapes', 'parcours-oauth', 'tenantA'
FROM unnest(ARRAY[
  '00000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000002',
  '00000000-0000-0000-0000-000000000003',
  '00000000-0000-0000-0000-000000000065'
]) subject;
INSERT INTO permissions_attributes(permission_id, attribute)
SELECT id, '[{"key":"profession","operator":"IS","value":["nurse"]}]'::jsonb
FROM permissions WHERE object_id='parcours-oauth' AND relation='can_read';
COMMIT;
""")
            docker("exec", "-i", postgres, "psql", "-X", "-v", "ON_ERROR_STOP=1",
                   "-U", "postgres", "-d", "validation", input_text="\n".join(sql))
            conninfo = (
                "host=localhost port=5432 dbname=validation user=read_validation "
                f"sslmode=verify-full sslrootcert=/certs/ca.crt oauth_issuer={ISSUER} "
                "oauth_client_id=postgres-test connect_timeout=5"
            )

            def decide(label: str, bearer: str, expected: str | int,
                       diagnostic: str | None = None) -> None:
                previous_logs = docker("logs", postgres).stderr if diagnostic else ""
                result = docker(
                    "exec", "-i", "--env", f"ADAM_OAUTH_CONNINFO={conninfo}",
                    postgres, "/tmp/client", input_text=bearer + "\n", check=False,
                )
                if isinstance(expected, int):
                    if result.returncode != expected:
                        raise AssertionError(
                            f"{label}: expected exit {expected}, got {result.returncode}; {result.stderr}"
                        )
                elif result.returncode or result.stdout.strip() != expected:
                    logs = docker("logs", postgres).stderr.splitlines()
                    details = "\n".join(line for line in logs if "DETAIL:  validator=" in line)
                    raise AssertionError(f"{label}: unexpected result; {result.stderr}{details}")
                if diagnostic:
                    new_logs = docker("logs", postgres).stderr[len(previous_logs):]
                    if diagnostic not in new_logs:
                        raise AssertionError(f"{label}: expected validator diagnostic {diagnostic}")
                print(f"PASS: {label}")

            first_token = token("nurse")
            decide("authorized practitioner", first_token, "1")
            decide("wrong profession", token("doctor"), "0")
            decide("wrong tenant", token("wrong-tenant"), "0")
            decide("other subject", token("other-subject"), "0")
            decide("missing profession", token("missing-profession"), 3)
            decide("missing tenant", token("missing-tenant"), 3)
            decide("unmapped identity", token("unmapped"), 2)
            decide("wrong audience", token("nurse", client_id="wrong-audience"), 2,
                   "claims=invalid_audience")
            decide("wrong scope", token("nurse", scope="openid"), 2,
                   "claims=insufficient_scope")
            decide("wrong issuer", token("nurse", realm_name="other"), 2)
            parts = first_token.split(".")
            parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
            decide("modified signature", ".".join(parts), 2)
            decide("authorized after rejections", token("nurse"), "1")
            print("Waiting for the first token to expire...")
            time.sleep(32)
            decide("expired token", first_token, 2, "claims=expired")
            print(docker("exec", postgres, "postgres", "--version").stdout.strip())
    finally:
        cleanup_errors = []
        for name in reversed(created):
            result = docker("rm", "--force", name, check=False)
            if result.returncode:
                cleanup_errors.append(f"container {name}: {result.stderr.strip()}")
        if volume_created:
            result = docker("volume", "rm", certs, check=False)
            if result.returncode:
                cleanup_errors.append(f"volume {certs}: {result.stderr.strip()}")
        if cleanup_errors:
            raise RuntimeError("Cleanup failed:\n" + "\n".join(cleanup_errors))


if __name__ == "__main__":
    main()
