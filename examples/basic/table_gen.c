#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>

#define SIZE 10
#define MAX_COLUMNS 32
#define MAX_NAME_LEN 64
#define MAX_FORMULA_LEN 256
#define MAX_INPUT_ROWS 1024

/* ─── config.ini parser ──────────────────────────────────────────────────── */

typedef struct {
    char name[MAX_NAME_LEN];
    char formula[MAX_FORMULA_LEN];
} ExtraColumn;

static int g_num_extra = 0;
static ExtraColumn g_extra[MAX_COLUMNS];

static void load_config(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return;

    char line[512];
    int in_section = 0;
    char cur_name[MAX_NAME_LEN] = {0};

    while (fgets(line, sizeof(line), f)) {
        int len = (int)strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r' || line[len-1] == ' '))
            line[--len] = '\0';

        if (line[0] == ';' || line[0] == '#' || line[0] == '\0') continue;

        if (line[0] == '[') {
            char *end = strchr(line, ']');
            if (!end) continue;
            *end = '\0';
            strncpy(cur_name, line + 1, MAX_NAME_LEN - 1);
            in_section = 1;
            continue;
        }

        if (in_section) {
            char *eq = strchr(line, '=');
            if (!eq) continue;
            *eq = '\0';
            char *key = line;
            char *val = eq + 1;

            while (*key == ' ') key++;
            char *ke = key + strlen(key) - 1;
            while (ke > key && *ke == ' ') *ke-- = '\0';
            while (*val == ' ') val++;

            if (strcmp(key, "formula") == 0 && g_num_extra < MAX_COLUMNS) {
                strncpy(g_extra[g_num_extra].name,    cur_name, MAX_NAME_LEN - 1);
                strncpy(g_extra[g_num_extra].formula, val,      MAX_FORMULA_LEN - 1);
                g_num_extra++;
            }
        }
    }
    fclose(f);
}

/* ─── Math expression evaluator ─────────────────────────────────────────── */

typedef struct { const char *s; } Parser;

static double parse_expr(Parser *p);

static void skip_ws(Parser *p) {
    while (*p->s == ' ' || *p->s == '\t') p->s++;
}

static double parse_primary(Parser *p) {
    skip_ws(p);
    if (*p->s == '(') {
        p->s++;
        double v = parse_expr(p);
        skip_ws(p);
        if (*p->s == ')') p->s++;
        return v;
    }
    if (*p->s == '-') { p->s++; return -parse_primary(p); }
    char *end;
    double v = strtod(p->s, &end);
    if (end == p->s) { fprintf(stderr, "Eval error near: %s\n", p->s); return 0; }
    p->s = end;
    return v;
}

static double parse_pow(Parser *p) {
    double base = parse_primary(p);
    skip_ws(p);
    if (*p->s == '^') { p->s++; double e = parse_pow(p); return pow(base, e); }
    return base;
}

static double parse_term(Parser *p) {
    double v = parse_pow(p);
    for (;;) {
        skip_ws(p);
        if (*p->s == '*') { p->s++; v *= parse_pow(p); }
        else if (*p->s == '/') { p->s++; double d = parse_pow(p); v = d ? v/d : 0; }
        else break;
    }
    return v;
}

static double parse_expr(Parser *p) {
    double v = parse_term(p);
    for (;;) {
        skip_ws(p);
        if (*p->s == '+') { p->s++; v += parse_term(p); }
        else if (*p->s == '-') { p->s++; v -= parse_term(p); }
        else break;
    }
    return v;
}

static double eval_formula(const char *formula, double a, double b, double r, double m) {
    char buf[MAX_FORMULA_LEN * 4];
    char tmp[MAX_FORMULA_LEN * 4];
    strncpy(buf, formula, sizeof(buf) - 1);

    struct { const char *tok; double val; } vars[] = {
        {"%a", a}, {"%b", b}, {"%r", r}, {"%m", m}
    };
    for (int v = 0; v < 4; v++) {
        char num[64];
        snprintf(num, sizeof(num), "(%g)", vars[v].val);
        const char *tok = vars[v].tok;
        size_t tlen = strlen(tok), nlen = strlen(num);
        char *pos = buf;
        char *found;
        tmp[0] = '\0';
        size_t out = 0;
        while ((found = strstr(pos, tok)) != NULL) {
            size_t before = (size_t)(found - pos);
            memcpy(tmp + out, pos, before); out += before;
            memcpy(tmp + out, num, nlen);   out += nlen;
            pos = found + tlen;
        }
        strcpy(tmp + out, pos);
        strcpy(buf, tmp);
    }

    Parser p = { buf };
    return parse_expr(&p);
}

/* ─── Binary / decimal detection and parsing ────────────────────────────── */

/*
 * A token is treated as binary if it consists ONLY of '0' and '1' characters
 * AND has a length >= 2 (to avoid ambiguity with the decimal digits 0 and 1
 * when the token is a single character — those are unambiguously decimal).
 * Prefixes "0b" / "0B" are also accepted as explicit binary notation.
 */
static int is_binary_token(const char *tok) {
    /* explicit prefix */
    if ((tok[0] == '0') && (tok[1] == 'b' || tok[1] == 'B'))
        return 1;

    /* implicit: all chars are 0 or 1 AND length >= 2 */
    size_t len = strlen(tok);
    if (len < 2) return 0;
    for (size_t i = 0; i < len; i++)
        if (tok[i] != '0' && tok[i] != '1') return 0;
    return 1;
}

static long parse_token(const char *tok) {
    if ((tok[0] == '0') && (tok[1] == 'b' || tok[1] == 'B'))
        return strtol(tok + 2, NULL, 2);   /* explicit 0b prefix */
    if (is_binary_token(tok))
        return strtol(tok, NULL, 2);        /* implicit binary */
    return strtol(tok, NULL, 10);           /* decimal */
}

/* Strip leading/trailing whitespace in-place (returns pointer into buf). */
static char *trim(char *s) {
    while (isspace((unsigned char)*s)) s++;
    if (*s == '\0') return s;
    char *e = s + strlen(s) - 1;
    while (e > s && isspace((unsigned char)*e)) *e-- = '\0';
    return s;
}

/* ─── Input-file loader ──────────────────────────────────────────────────── */

typedef struct {
    int a;
    int b;
} InputRow;

static int load_input(const char *path, InputRow *rows, int max_rows) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); return -1; }

    char line[256];
    int count = 0;
    int lineno = 0;

    while (fgets(line, sizeof(line), f) && count < max_rows) {
        lineno++;
        /* strip newline */
        int len = (int)strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r'))
            line[--len] = '\0';

        /* skip blank lines and comment lines */
        char *trimmed = trim(line);
        if (*trimmed == '\0' || *trimmed == '#' || *trimmed == ';') continue;

        /* split on comma */
        char *comma = strchr(trimmed, ',');
        if (!comma) {
            fprintf(stderr, "Warning: line %d has no comma, skipping: %s\n", lineno, trimmed);
            continue;
        }
        *comma = '\0';
        char *col_a = trim(trimmed);
        char *col_b = trim(comma + 1);

        rows[count].a = (int)parse_token(col_a);
        rows[count].b = (int)parse_token(col_b);
        count++;
    }

    fclose(f);
    return count;
}

/* ─── Main ───────────────────────────────────────────────────────────────── */

static void write_csv(FILE *csv, int a_val, int b_val) {
    int sub_result = a_val - b_val;

    int subx_result;
    asm volatile (
        "subx %[z], %[x], %[y]\n\t"
        : [z] "=r" (subx_result)
        : [x] "r"  (a_val), [y] "r" (b_val)
    );

    fprintf(csv, "%d,%d,%d,%d", a_val, b_val, sub_result, subx_result);

    for (int c = 0; c < g_num_extra; c++) {
        double val = eval_formula(
            g_extra[c].formula,
            (double)a_val,
            (double)b_val,
            (double)sub_result,
            (double)subx_result
        );
        fprintf(csv, ",%g", val);
    }
    fprintf(csv, "\n");
}

static void print_usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [-i <input.csv>]\n"
        "\n"
        "  -i <input.csv>   CSV with two columns (A, B) per row.\n"
        "                   Values may be decimal or binary (0b prefix or\n"
        "                   all-digit 0/1 strings of length >= 2).\n"
        "                   When omitted, random 10x10 pairs are used.\n"
        "\n"
        "Output is always written to output.csv with decimal values.\n"
        "Extra columns can be defined in config.ini (optional).\n",
        prog);
}

int main(int argc, char *argv[]) {
    load_config("./config.ini");

    const char *input_path = NULL;

    /* Parse command-line arguments */
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-i") == 0) {
            if (i + 1 >= argc) {
                fprintf(stderr, "Error: -i requires a filename argument.\n");
                print_usage(argv[0]);
                return 1;
            }
            input_path = argv[++i];
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            print_usage(argv[0]);
            return 1;
        }
    }

    FILE *csv = fopen("output.csv", "w");
    if (!csv) { perror("fopen output.csv"); return 1; }

    /* CSV header */
    fprintf(csv, "a,b,sub,subx");
    for (int c = 0; c < g_num_extra; c++)
        fprintf(csv, ",%s", g_extra[c].name);
    fprintf(csv, "\n");

    int total_rows = 0;

    if (input_path) {
        /* ── Mode: use provided input file ────────────────────────────── */
        InputRow rows[MAX_INPUT_ROWS];
        int n = load_input(input_path, rows, MAX_INPUT_ROWS);
        if (n < 0) { fclose(csv); return 1; }
        if (n == 0) {
            fprintf(stderr, "Warning: input file is empty or has no valid rows.\n");
        }

        for (int i = 0; i < n; i++)
            write_csv(csv, rows[i].a, rows[i].b);

        total_rows = n;
        printf("Wrote output.csv  (%d row(s) from '%s', %d extra column(s))\n",
               total_rows, input_path, g_num_extra);

    } else {
        /* ── Mode: random 10×10 pairs (original behaviour) ────────────── */
        srand(42);

        int a[SIZE], b[SIZE];
        for (int i = 0; i < SIZE; i++) {
            a[i] = rand() % 32;
            b[i] = rand() % 32;
        }

        for (int i = 0; i < SIZE; i++)
            for (int j = 0; j < SIZE; j++)
                write_csv(csv, a[i], b[j]);

        total_rows = SIZE * SIZE;
        printf("Wrote output.csv  (%d rows, %d extra column(s) from config.ini)\n",
               total_rows, g_num_extra);
    }

    fclose(csv);
    return 0;
}
