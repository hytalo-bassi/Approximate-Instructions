/*
 * common_api.h
 *
 * Single-header C API for producing a result report as JSON, matching the
 * schema:
 *
 *   {
 *     "final_value": <number>,
 *     "history": [ ... ],
 *     "execution_count": { "<key>": <int>, ... },
 *     "metadata": { "<key>": <value>, ... }
 *   }
 *
 * Usage:
 *   #define COMMON_API_IMPLEMENTATION
 *   #include "common_api.h"
 *
 *   int main(void) {
 *       common_api_init();
 *
 *       common_api_set_final_value(42.0);
 *       common_api_history_push_number(1.0);
 *       common_api_history_push_string("checkpoint");
 *       common_api_history_increment("loop_iters");   // ++execution_count["loop_iters"]
 *       common_api_history_increment("loop_iters");   // now == 2
 *       common_api_metadata_set_string("run_by", "hytalo");
 *       common_api_metadata_set_number("clock_ghz", 1.0);
 *
 *       common_api_output("result");  // writes ./result.json
 *
 *       common_api_free();
 *       return 0;
 *   }
 *
 * Design notes:
 *   - No external dependencies (no cJSON, no libc beyond stdio/stdlib/string/
 *     stdint) so it can be compiled with riscv64-unknown-linux-musl-gcc and
 *     dropped straight into the gem5 benchmark sources.
 *   - All containers (history array, execution_count map, metadata map) grow
 *     dynamically; no fixed capacity.
 *   - history entries can be numbers, strings, or bools ("list[any]").
 *   - metadata entries can be numbers, strings, or bools ("dict[str, Any]").
 *   - Only one translation unit should define COMMON_API_IMPLEMENTATION.
 */

#ifndef COMMON_API_H
#define COMMON_API_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stddef.h>

/* ------------------------------------------------------------------ */
/* Public API                                                          */
/* ------------------------------------------------------------------ */

/* Must be called once before any other common_api_* call. Resets all
 * internal state (safe to call again to start a fresh report). */
void common_api_init(void);

/* Frees all internal state. Call after common_api_output() if you want to
 * release memory (not required if the process is about to exit). */
void common_api_free(void);

/* Sets the top-level "final_value" field. Overwrites any previous value. */
void common_api_set_final_value(double value);

/* Appends an entry to the "history" list. */
void common_api_history_push_number(double value);
void common_api_history_push_string(const char *value);
void common_api_history_push_bool(int value); /* 0 = false, nonzero = true */

/* Increments execution_count[key] by 1 (creating it at 0 -> 1 if it doesn't
 * exist yet). This is the "history_increment" helper requested: */
void common_api_history_increment(const char *key);

/* Adds/overwrites a raw integer count for execution_count[key]. */
void common_api_execution_count_set(const char *key, long value);

/* Sets metadata[key] = value, for the supported value types. Calling this
 * again with the same key overwrites the previous value. */
void common_api_metadata_set_number(const char *key, double value);
void common_api_metadata_set_string(const char *key, const char *value);
void common_api_metadata_set_bool(const char *key, int value);

/* Serializes the full report and writes it to "<filename>.json" in the
 * current working directory. Returns 0 on success, nonzero on failure
 * (e.g. could not open file for writing). */
int common_api_output(const char *filename);

#ifdef __cplusplus
}
#endif

#endif /* COMMON_API_H */

/* ==================================================================== */
/* Implementation                                                        */
/* ==================================================================== */
#ifdef COMMON_API_IMPLEMENTATION

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ---- value tagging, used by both history[] and metadata{} ---- */

typedef enum {
    CAPI_NUMBER,
    CAPI_STRING,
    CAPI_BOOL
} capi_value_type;

typedef struct {
    capi_value_type type;
    union {
        double number;
        char  *string; /* heap-owned copy */
        int    boolean;
    } as;
} capi_value;

/* ---- history: list[any] ---- */

typedef struct {
    capi_value *items;
    size_t      count;
    size_t      capacity;
} capi_history_list;

/* ---- execution_count: dict[str -> int] ---- */

typedef struct {
    char *key;   /* heap-owned copy */
    long  value;
} capi_count_entry;

typedef struct {
    capi_count_entry *items;
    size_t            count;
    size_t            capacity;
} capi_count_map;

/* ---- metadata: dict[str -> any] ---- */

typedef struct {
    char       *key; /* heap-owned copy */
    capi_value  value;
} capi_meta_entry;

typedef struct {
    capi_meta_entry *items;
    size_t           count;
    size_t           capacity;
} capi_meta_map;

/* ---- global report state ---- */

static struct {
    int    has_final_value;
    double final_value;

    capi_history_list history;
    capi_count_map    execution_count;
    capi_meta_map     metadata;
} g_capi_report;

/* ------------------------------------------------------------------ */
/* internal helpers                                                     */
/* ------------------------------------------------------------------ */

static char *capi_strdup(const char *s) {
    if (!s) s = "";
    size_t len = strlen(s) + 1;
    char *copy = (char *)malloc(len);
    if (copy) memcpy(copy, s, len);
    return copy;
}

static void capi_history_ensure_capacity(capi_history_list *list, size_t needed) {
    if (needed <= list->capacity) return;
    size_t new_cap = list->capacity ? list->capacity * 2 : 8;
    while (new_cap < needed) new_cap *= 2;
    list->items = (capi_value *)realloc(list->items, new_cap * sizeof(capi_value));
    list->capacity = new_cap;
}

static void capi_count_ensure_capacity(capi_count_map *map, size_t needed) {
    if (needed <= map->capacity) return;
    size_t new_cap = map->capacity ? map->capacity * 2 : 8;
    while (new_cap < needed) new_cap *= 2;
    map->items = (capi_count_entry *)realloc(map->items, new_cap * sizeof(capi_count_entry));
    map->capacity = new_cap;
}

static void capi_meta_ensure_capacity(capi_meta_map *map, size_t needed) {
    if (needed <= map->capacity) return;
    size_t new_cap = map->capacity ? map->capacity * 2 : 8;
    while (new_cap < needed) new_cap *= 2;
    map->items = (capi_meta_entry *)realloc(map->items, new_cap * sizeof(capi_meta_entry));
    map->capacity = new_cap;
}

/* Finds an execution_count entry by key, or NULL if not present. */
static capi_count_entry *capi_count_find(capi_count_map *map, const char *key) {
    for (size_t i = 0; i < map->count; i++) {
        if (strcmp(map->items[i].key, key) == 0) return &map->items[i];
    }
    return NULL;
}

/* Finds a metadata entry by key, or NULL if not present. */
static capi_meta_entry *capi_meta_find(capi_meta_map *map, const char *key) {
    for (size_t i = 0; i < map->count; i++) {
        if (strcmp(map->items[i].key, key) == 0) return &map->items[i];
    }
    return NULL;
}

static void capi_free_value(capi_value *v) {
    if (v->type == CAPI_STRING) {
        free(v->as.string);
        v->as.string = NULL;
    }
}

/* Writes a JSON-escaped string (including surrounding quotes) to fp. */
static void capi_write_json_string(FILE *fp, const char *s) {
    fputc('"', fp);
    for (const unsigned char *p = (const unsigned char *)s; *p; p++) {
        switch (*p) {
            case '"':  fputs("\\\"", fp); break;
            case '\\': fputs("\\\\", fp); break;
            case '\n': fputs("\\n", fp);  break;
            case '\r': fputs("\\r", fp);  break;
            case '\t': fputs("\\t", fp);  break;
            default:
                if (*p < 0x20) {
                    fprintf(fp, "\\u%04x", *p);
                } else {
                    fputc(*p, fp);
                }
        }
    }
    fputc('"', fp);
}

static void capi_write_value(FILE *fp, const capi_value *v) {
    switch (v->type) {
        case CAPI_NUMBER:
            fprintf(fp, "%.17g", v->as.number);
            break;
        case CAPI_STRING:
            capi_write_json_string(fp, v->as.string ? v->as.string : "");
            break;
        case CAPI_BOOL:
            fputs(v->as.boolean ? "true" : "false", fp);
            break;
    }
}

/* ------------------------------------------------------------------ */
/* public API implementation                                            */
/* ------------------------------------------------------------------ */

void common_api_init(void) {
    /* Free any previous state first, in case init() is called again. */
    common_api_free();
    memset(&g_capi_report, 0, sizeof(g_capi_report));
}

void common_api_free(void) {
    for (size_t i = 0; i < g_capi_report.history.count; i++) {
        capi_free_value(&g_capi_report.history.items[i]);
    }
    free(g_capi_report.history.items);

    for (size_t i = 0; i < g_capi_report.execution_count.count; i++) {
        free(g_capi_report.execution_count.items[i].key);
    }
    free(g_capi_report.execution_count.items);

    for (size_t i = 0; i < g_capi_report.metadata.count; i++) {
        free(g_capi_report.metadata.items[i].key);
        capi_free_value(&g_capi_report.metadata.items[i].value);
    }
    free(g_capi_report.metadata.items);

    memset(&g_capi_report, 0, sizeof(g_capi_report));
}

void common_api_set_final_value(double value) {
    g_capi_report.has_final_value = 1;
    g_capi_report.final_value = value;
}

static void capi_history_push(capi_value v) {
    capi_history_list *list = &g_capi_report.history;
    capi_history_ensure_capacity(list, list->count + 1);
    list->items[list->count++] = v;
}

void common_api_history_push_number(double value) {
    capi_value v;
    v.type = CAPI_NUMBER;
    v.as.number = value;
    capi_history_push(v);
}

void common_api_history_push_string(const char *value) {
    capi_value v;
    v.type = CAPI_STRING;
    v.as.string = capi_strdup(value);
    capi_history_push(v);
}

void common_api_history_push_bool(int value) {
    capi_value v;
    v.type = CAPI_BOOL;
    v.as.boolean = value ? 1 : 0;
    capi_history_push(v);
}

void common_api_history_increment(const char *key) {
    capi_count_map *map = &g_capi_report.execution_count;
    capi_count_entry *entry = capi_count_find(map, key);
    if (entry) {
        entry->value += 1;
        return;
    }
    capi_count_ensure_capacity(map, map->count + 1);
    map->items[map->count].key = capi_strdup(key);
    map->items[map->count].value = 1;
    map->count += 1;
}

void common_api_execution_count_set(const char *key, long value) {
    capi_count_map *map = &g_capi_report.execution_count;
    capi_count_entry *entry = capi_count_find(map, key);
    if (entry) {
        entry->value = value;
        return;
    }
    capi_count_ensure_capacity(map, map->count + 1);
    map->items[map->count].key = capi_strdup(key);
    map->items[map->count].value = value;
    map->count += 1;
}

static capi_meta_entry *capi_meta_upsert(const char *key) {
    capi_meta_map *map = &g_capi_report.metadata;
    capi_meta_entry *entry = capi_meta_find(map, key);
    if (entry) {
        capi_free_value(&entry->value);
        return entry;
    }
    capi_meta_ensure_capacity(map, map->count + 1);
    entry = &map->items[map->count];
    entry->key = capi_strdup(key);
    map->count += 1;
    return entry;
}

void common_api_metadata_set_number(const char *key, double value) {
    capi_meta_entry *entry = capi_meta_upsert(key);
    entry->value.type = CAPI_NUMBER;
    entry->value.as.number = value;
}

void common_api_metadata_set_string(const char *key, const char *value) {
    capi_meta_entry *entry = capi_meta_upsert(key);
    entry->value.type = CAPI_STRING;
    entry->value.as.string = capi_strdup(value);
}

void common_api_metadata_set_bool(const char *key, int value) {
    capi_meta_entry *entry = capi_meta_upsert(key);
    entry->value.type = CAPI_BOOL;
    entry->value.as.boolean = value ? 1 : 0;
}

int common_api_output(const char *filename) {
    if (!filename || !*filename) return 1;

    /* filename + ".json" + null terminator */
    size_t path_len = strlen(filename) + 6;
    char *path = (char *)malloc(path_len);
    if (!path) return 1;
    snprintf(path, path_len, "%s.json", filename);

    FILE *fp = fopen(path, "w");
    free(path);
    if (!fp) return 1;

    fputs("{\n", fp);

    /* final_value */
    fputs("  \"final_value\": ", fp);
    if (g_capi_report.has_final_value) {
        fprintf(fp, "%.17g", g_capi_report.final_value);
    } else {
        fputs("null", fp);
    }
    fputs(",\n", fp);

    /* history */
    fputs("  \"history\": [", fp);
    for (size_t i = 0; i < g_capi_report.history.count; i++) {
        if (i > 0) fputs(", ", fp);
        capi_write_value(fp, &g_capi_report.history.items[i]);
    }
    fputs("],\n", fp);

    /* execution_count */
    fputs("  \"execution_count\": {", fp);
    for (size_t i = 0; i < g_capi_report.execution_count.count; i++) {
        if (i > 0) fputs(", ", fp);
        capi_write_json_string(fp, g_capi_report.execution_count.items[i].key);
        fprintf(fp, ": %ld", g_capi_report.execution_count.items[i].value);
    }
    fputs("},\n", fp);

    /* metadata */
    fputs("  \"metadata\": {", fp);
    for (size_t i = 0; i < g_capi_report.metadata.count; i++) {
        if (i > 0) fputs(", ", fp);
        capi_write_json_string(fp, g_capi_report.metadata.items[i].key);
        fputs(": ", fp);
        capi_write_value(fp, &g_capi_report.metadata.items[i].value);
    }
    fputs("}\n", fp);

    fputs("}\n", fp);

    fclose(fp);
    return 0;
}

#endif /* COMMON_API_IMPLEMENTATION */