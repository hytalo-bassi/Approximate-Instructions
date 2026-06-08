#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
#include "../utils/instructions.h"

#define SIZE          10
#define MAX_COLUMNS   32
#define MAX_NAME_LEN  64
#define MAX_FORMULA_LEN 256
#define MAX_INPUT_ROWS  1024
#define MAX_INSTRUCTIONS 32

/* ─── Instruction descriptor ─────────────────────────────────────────────── */

/*
 * Each entry maps a mnemonic to:
 *   - its approximate counterpart name (for the CSV header / verbose output)
 *   - whether its operands / result are floating-point
 *   - function pointers for the exact and approximate operations
 */
typedef double (*OpFn)(double, double);

typedef struct {
    const char *name;       /* e.g. "add"   */
    const char *approx_name;/* e.g. "addx"  */
    int         is_float;   /* 1 → generate float randoms, 0 → integer randoms */
    OpFn        exact;
    OpFn        approx;
} InstrDesc;

/* Exact wrappers (operate on doubles; integer ops truncate naturally) */
static double op_add (double a, double b) { return a + b; }
static double op_sub (double a, double b) { return a - b; }
static double op_mul (double a, double b) { return a * b; }
static double op_div (double a, double b) { return b != 0.0 ? a / b : 0.0; }
static double op_rem (double a, double b) {
    long ai = (long)a, bi = (long)b;
    return bi ? (double)(ai % bi) : 0.0;
}
static double op_fadd(double a, double b) { return a + b; }
static double op_fsub(double a, double b) { return a - b; }
static double op_fmul(double a, double b) { return a * b; }
static double op_fdiv(double a, double b) { return b != 0.0 ? a / b : 0.0; }

/* Approximate wrappers — call into utils/instructions.h */
static double op_addx (double a, double b) { return (double)addx ((int)a, (int)b); }
static double op_subx (double a, double b) { return (double)subx ((int)a, (int)b); }
static double op_mulx (double a, double b) { return (double)mulx ((int)a, (int)b); }
static double op_divx (double a, double b) { return (double)divx ((int)a, (int)b); }
static double op_faddx(double a, double b) { return faddx(a, b); }
static double op_fsubx(double a, double b) { return fsubx(a, b); }
static double op_fmulx(double a, double b) { return fmulx(a, b); }
static double op_fdivx(double a, double b) { return fdivx(a, b); }

static const InstrDesc INSTR_TABLE[] = {
    /* name    approx     float  exact       approx       */
    { "add",  "addx",   0,  op_add,   op_addx  },
    { "sub",  "subx",   0,  op_sub,   op_subx  },
    { "mul",  "mulx",   0,  op_mul,   op_mulx  },
    { "div",  "divx",   0,  op_div,   op_divx  },
    { "fadd", "faddx",  1,  op_fadd,  op_faddx },
    { "fsub", "fsubx",  1,  op_fsub,  op_fsubx },
    { "fmul", "fmulx",  1,  op_fmul,  op_fmulx },
    { "fdiv", "fdivx",  1,  op_fdiv,  op_fdivx },
};
static const int INSTR_TABLE_LEN = (int)(sizeof(INSTR_TABLE) / sizeof(INSTR_TABLE[0]));

static const InstrDesc *find_instr(const char *name) {
    for (int i = 0; i < INSTR_TABLE_LEN; i++)
        if (strcmp(INSTR_TABLE[i].name, name) == 0)
            return &INSTR_TABLE[i];
    return NULL;
}

/* ─── config.ini parser ──────────────────────────────────────────────────── */

typedef struct {
    char name[MAX_NAME_LEN];
    char formula[MAX_FORMULA_LEN];
} ExtraColumn;

static int   g_num_extra = 0;
static ExtraColumn g_extra[MAX_COLUMNS];

/* Instructions parsed from config.ini */
static int   g_num_instrs = 0;
static char  g_instr_names[MAX_INSTRUCTIONS][MAX_NAME_LEN];

static void load_config(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return;

    char line[512];
    int  in_section = 0;
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

        {
            char *eq = strchr(line, '=');
            if (!eq) continue;
            *eq = '\0';
            char *key = line;
            char *val = eq + 1;

            /* trim key */
            while (*key == ' ') key++;
            char *ke = key + strlen(key) - 1;
            while (ke > key && *ke == ' ') *ke-- = '\0';
            /* trim val */
            while (*val == ' ') val++;

            /*
             * "formula" needs cur_name (the enclosing section header) as the
             * column name, so it is only valid inside a section.
             */
            if (in_section && strcmp(key, "formula") == 0 && g_num_extra < MAX_COLUMNS) {
                strncpy(g_extra[g_num_extra].name,    cur_name, MAX_NAME_LEN - 1);
                strncpy(g_extra[g_num_extra].formula, val,      MAX_FORMULA_LEN - 1);
                g_num_extra++;
            }

            /*
             * "instructions" is only read from the [global] section.
             */
            if (in_section && strcmp(cur_name, "global") == 0
                    && strcmp(key, "instructions") == 0) {
                char vbuf[512];
                strncpy(vbuf, val, sizeof(vbuf) - 1);
                char *tok = strtok(vbuf, ",");
                while (tok && g_num_instrs < MAX_INSTRUCTIONS) {
                    while (*tok == ' ') tok++;
                    char *te = tok + strlen(tok) - 1;
                    while (te > tok && *te == ' ') *te-- = '\0';
                    if (*tok) {
                        strncpy(g_instr_names[g_num_instrs], tok, MAX_NAME_LEN - 1);
                        g_num_instrs++;
                    }
                    tok = strtok(NULL, ",");
                }
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

static double eval_formula(const char *formula,
                            double a, double b, double r, double m) {
    char buf[MAX_FORMULA_LEN * 4];
    char tmp[MAX_FORMULA_LEN * 4];
    strncpy(buf, formula, sizeof(buf) - 1);

    struct { const char *tok; double val; } vars[] = {
        {"%a", a}, {"%b", b}, {"%r", r}, {"%m", m}
    };
    for (int v = 0; v < 4; v++) {
        char num[64];
        snprintf(num, sizeof(num), "(%g)", vars[v].val);
        const char *tok  = vars[v].tok;
        size_t tlen = strlen(tok), nlen = strlen(num);
        char  *pos  = buf, *found;
        tmp[0] = '\0';
        size_t out  = 0;
        while ((found = strstr(pos, tok)) != NULL) {
            size_t before = (size_t)(found - pos);
            memcpy(tmp + out, pos,   before); out += before;
            memcpy(tmp + out, num,   nlen);   out += nlen;
            pos = found + tlen;
        }
        strcpy(tmp + out, pos);
        strcpy(buf, tmp);
    }
    Parser p = { buf };
    return parse_expr(&p);
}

/* ─── Token / trim helpers ───────────────────────────────────────────────── */

static char *trim(char *s) {
    while (isspace((unsigned char)*s)) s++;
    if (*s == '\0') return s;
    char *e = s + strlen(s) - 1;
    while (e > s && isspace((unsigned char)*e)) *e-- = '\0';
    return s;
}

static double parse_token(const char *tok) {
    char *end;
    double v = strtod(tok, &end);
    if (end == tok) {
        fprintf(stderr, "Warning: could not parse value '%s', using 0.0\n", tok);
        return 0.0;
    }
    return v;
}

/* ─── Input-file loader ──────────────────────────────────────────────────── */

typedef struct { double a, b; } InputRow;

static int load_input(const char *path, InputRow *rows, int max_rows) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); return -1; }

    char line[256];
    int  count = 0, lineno = 0;

    while (fgets(line, sizeof(line), f) && count < max_rows) {
        lineno++;
        int len = (int)strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r'))
            line[--len] = '\0';

        char *trimmed = trim(line);
        if (*trimmed == '\0' || *trimmed == '#' || *trimmed == ';') continue;

        char *comma = strchr(trimmed, ',');
        if (!comma) {
            fprintf(stderr, "Warning: line %d has no comma, skipping: %s\n",
                    lineno, trimmed);
            continue;
        }
        *comma = '\0';
        rows[count].a = parse_token(trim(trimmed));
        rows[count].b = parse_token(trim(comma + 1));
        count++;
    }
    fclose(f);
    return count;
}

/* ─── Per-instruction CSV writer ─────────────────────────────────────────── */

static void write_row(FILE *csv, const InstrDesc *instr,
                      double a_val, double b_val) {
    double exact_result  = instr->exact (a_val, b_val);
    double approx_result = instr->approx(a_val, b_val);

    fprintf(csv, "%g,%g,%g,%g", a_val, b_val, exact_result, approx_result);

    for (int c = 0; c < g_num_extra; c++) {
        double val = eval_formula(g_extra[c].formula,
                                  a_val, b_val,
                                  exact_result, approx_result);
        fprintf(csv, ",%g", val);
    }
    fprintf(csv, "\n");
}

static void run_instruction(const InstrDesc *instr, const char *input_path) {
    /* ── Verbose banner ─────────────────────────────────────────────── */
    printf("Instruction: %s / %s  (%s operands)\n",
           instr->name, instr->approx_name,
           instr->is_float ? "floating-point" : "integer");

    /* ── Open output CSV ────────────────────────────────────────────── */
    char outname[128];
    snprintf(outname, sizeof(outname), "output-%s.csv", instr->name);
    printf("Output file: %s\n", outname);

    FILE *csv = fopen(outname, "w");
    if (!csv) { perror(outname); return; }

    /* header */
    fprintf(csv, "a,b,%s,%s", instr->name, instr->approx_name);
    for (int c = 0; c < g_num_extra; c++)
        fprintf(csv, ",%s", g_extra[c].name);
    fprintf(csv, "\n");

    int total_rows = 0;

    if (input_path) {
        /* ── File mode ──────────────────────────────────────────────── */
        InputRow rows[MAX_INPUT_ROWS];
        int n = load_input(input_path, rows, MAX_INPUT_ROWS);
        if (n < 0) { fclose(csv); return; }
        if (n == 0)
            fprintf(stderr, "  Warning: input file is empty or has no valid rows.\n");

        for (int i = 0; i < n; i++)
            write_row(csv, instr, rows[i].a, rows[i].b);
        total_rows = n;

        printf("  Wrote %d row(s) from '%s', %d extra column(s)\n\n",
               total_rows, input_path, g_num_extra);

    } else {
        /* ── Random mode ────────────────────────────────────────────── */
        srand(42);

        double a[SIZE], b[SIZE];
        for (int i = 0; i < SIZE; i++) {
            if (instr->is_float) {
                /* floats in [0.0, 32.0) */
                a[i] = (rand() % 3200) / 100.0;
                b[i] = (rand() % 3200) / 100.0;
            } else {
                /* integers in [0, 32) */
                a[i] = (double)(rand() % 32);
                b[i] = (double)(rand() % 32);
            }
        }

        for (int i = 0; i < SIZE; i++)
            for (int j = 0; j < SIZE; j++)
                write_row(csv, instr, a[i], b[j]);

        total_rows = SIZE * SIZE;
        printf("  Wrote %d rows (random %s pairs), %d extra column(s)\n\n",
               total_rows,
               instr->is_float ? "float" : "integer",
               g_num_extra);
    }

    fclose(csv);
}

/* ─── Usage ──────────────────────────────────────────────────────────────── */

static void print_usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [-i <input.csv>]\n"
        "\n"
        "  -i <input.csv>   CSV with two columns (A, B) per row.\n"
        "                   Values may be any valid numeric literals.\n"
        "                   When omitted, random 10×10 pairs are used.\n"
        "\n"
        "Instructions to test are read from the [global] section of config.ini:\n"
        "  [global]\n"
        "  instructions = add, fadd, mul, ...\n"
        "Defaults to 'add' if [global] / instructions is absent.\n"
        "\n"
        "One output-<instruction>.csv is created per instruction.\n"
        "Columns: a, b, <instr> (exact), <approx_instr> (approximate).\n"
        "\n"
        "Supported instructions and their approximate counterparts:\n"
        "  add/addx  sub/subx  mul/mulx  div/divx  rem/remx\n"
        "  fadd/faddx  fsub/fsubx  fmul/fmulx  fdiv/fdivx\n"
        "\n"
        "Extra columns can be defined in config.ini:\n"
        "  [MyColumn]\n"
        "  formula = %%r - %%m\n"
        "  Variables: %%a, %%b, %%r (exact result), %%m (approx result).\n",
        prog);
}

/* ─── Main ───────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[]) {
    load_config("./config.ini");

    const char *input_path = NULL;

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

    /* Default to "add" when config.ini supplies no instructions field */
    if (g_num_instrs == 0) {
        strncpy(g_instr_names[0], "add", MAX_NAME_LEN - 1);
        g_num_instrs = 1;
        printf("No instructions specified in config.ini — defaulting to 'add'.\n\n");
    }

    for (int i = 0; i < g_num_instrs; i++) {
        const InstrDesc *instr = find_instr(g_instr_names[i]);
        if (!instr) {
            fprintf(stderr,
                "Warning: unknown instruction '%s', skipping.\n\n",
                g_instr_names[i]);
            continue;
        }
        run_instruction(instr, input_path);
    }

    return 0;
}