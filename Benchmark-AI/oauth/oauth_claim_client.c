#include <jansson.h>
#include <libpq-fe.h>
#include <openssl/evp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TOKEN_LIMIT 65536

static char token[TOKEN_LIMIT + 2];

static int provide_token(PGauthData type, PGconn *connection, void *data)
{
    (void) connection;
    if (type != PQAUTHDATA_OAUTH_BEARER_TOKEN)
        return 0;
    ((PGoauthBearerRequest *) data)->token = token;
    return 1;
}

static json_t *token_claims(void)
{
    const char *start = strchr(token, '.');
    const char *end = start ? strchr(start + 1, '.') : NULL;
    if (!start || !end || strchr(end + 1, '.'))
        return NULL;
    size_t len = (size_t) (end - ++start);
    if (len == 0 || len % 4 == 1 || len > TOKEN_LIMIT)
        return NULL;
    size_t padded = (len + 3) & ~(size_t) 3;
    unsigned char *encoded = malloc(padded + 1);
    unsigned char *decoded = malloc(padded + 1);
    if (!encoded || !decoded) {
        free(encoded);
        free(decoded);
        return NULL;
    }
    for (size_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char) start[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_')) {
            free(encoded);
            free(decoded);
            return NULL;
        }
        encoded[i] = c == '-' ? '+' : c == '_' ? '/' : c;
    }
    for (size_t i = len; i < padded; i++)
        encoded[i] = '=';
    encoded[padded] = '\0';
    int bytes = EVP_DecodeBlock(decoded, encoded, (int) padded);
    json_error_t error;
    json_t *claims = bytes < 0 ? NULL :
        json_loadb((char *) decoded, (size_t) bytes - (padded - len),
                   JSON_REJECT_DUPLICATES, &error);
    free(encoded);
    free(decoded);
    return claims;
}

static const char *required_string(json_t *claims, const char *name)
{
    json_t *value = json_object_get(claims, name);
    if (!json_is_string(value) || json_string_length(value) == 0 ||
        json_string_length(value) > 256 ||
        strlen(json_string_value(value)) != json_string_length(value))
        return NULL;
    return json_string_value(value);
}

static void report_sql_error(const char *stage, PGresult *result)
{
    const char *sqlstate = PQresultErrorField(result, PG_DIAG_SQLSTATE);
    fprintf(stderr, "%s failed (SQLSTATE %s)\n", stage, sqlstate ? sqlstate : "unknown");
}

int main(void)
{
    const char *conninfo = getenv("ADAM_OAUTH_CONNINFO");
    if (!conninfo || !fgets(token, sizeof(token), stdin)) {
        fprintf(stderr, "Missing connection configuration or token\n");
        return EXIT_FAILURE;
    }
    size_t length = strcspn(token, "\r\n");
    if (length == 0 || length > TOKEN_LIMIT || token[length] == '\0') {
        fprintf(stderr, "Invalid token input\n");
        return EXIT_FAILURE;
    }
    token[length] = '\0';
    PQsetAuthDataHook(provide_token);
    PGconn *connection = PQconnectdb(conninfo);
    if (PQstatus(connection) != CONNECTION_OK) {
        const char *error = PQerrorMessage(connection);
        if (error && !strstr(error, token))
            fprintf(stderr, "OAuth authentication failed: %s", error);
        else
            fprintf(stderr, "OAuth authentication failed\n");
        PQfinish(connection);
        return 2;
    }

    int status = 4;
    json_t *claims = token_claims();
    const char *subject = claims ? required_string(claims, "sub") : NULL;
    const char *tenant = claims ? required_string(claims, "tenant_id") : NULL;
    const char *profession = claims ? required_string(claims, "profession") : NULL;
    PGresult *identity = PQexec(connection, "SELECT system_user");
    if (!subject || !tenant || !profession ||
        PQresultStatus(identity) != PGRES_TUPLES_OK || PQntuples(identity) != 1 ||
        strncmp(PQgetvalue(identity, 0, 0), "oauth:", 6) != 0 ||
        strcmp(PQgetvalue(identity, 0, 0) + 6, subject) != 0) {
        fprintf(stderr, "Missing claims or authenticated identity mismatch\n");
        status = 3;
        goto cleanup;
    }

    PGresult *result = PQexec(connection, "BEGIN READ ONLY; SET LOCAL search_path TO adam, public");
    if (PQresultStatus(result) != PGRES_COMMAND_OK) {
        report_sql_error("Transaction start", result);
        PQclear(result);
        goto cleanup;
    }
    PQclear(result);
    const char *values[] = {subject, tenant, profession};
    result = PQexecParams(connection,
        "SELECT set_config('app.adam.user_id',$1,true), "
        "set_config('app.adam.tenant_id',$2,true), "
        "set_config('app.adam.user_attributes',"
        "jsonb_build_object('profession',$3::text)::text,true)",
        3, NULL, values, NULL, NULL, 0);
    if (PQresultStatus(result) != PGRES_TUPLES_OK) {
        report_sql_error("Claim provisioning", result);
        PQclear(result);
        goto cleanup;
    }
    PQclear(result);
    result = PQexec(connection, "SELECT count(*) FROM adam.protected_records "
                    "WHERE id = 'parcours-oauth'");
    if (PQresultStatus(result) != PGRES_TUPLES_OK || PQntuples(result) != 1) {
        report_sql_error("Protected query", result);
        PQclear(result);
        goto cleanup;
    }
    int rows = atoi(PQgetvalue(result, 0, 0));
    PQclear(result);
    result = PQexec(connection, "COMMIT");
    if (PQresultStatus(result) != PGRES_COMMAND_OK) {
        report_sql_error("Commit", result);
        PQclear(result);
        goto cleanup;
    }
    PQclear(result);
    result = PQexec(connection,
        "SELECT coalesce(current_setting('app.adam.user_id', true),'') = '' "
        "AND coalesce(current_setting('app.adam.tenant_id', true),'') = '' "
        "AND coalesce(current_setting('app.adam.user_attributes', true),'') = ''");
    if (PQresultStatus(result) == PGRES_TUPLES_OK &&
        PQntuples(result) == 1 && strcmp(PQgetvalue(result, 0, 0), "t") == 0) {
        printf("%d\n", rows);
        status = EXIT_SUCCESS;
    }
    PQclear(result);

cleanup:
    if (status != EXIT_SUCCESS)
        fprintf(stderr, "Protected request failed\n");
    PQclear(identity);
    if (claims)
        json_decref(claims);
    PQfinish(connection);
    memset(token, 0, sizeof(token));
    return status;
}
