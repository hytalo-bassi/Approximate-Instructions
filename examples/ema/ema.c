#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "utils/instructions.h"

#define COMMON_API_IMPLEMENTATION
#include "common.h"

int main(int argc, char *argv[]) {

    if (argc < 2) {
        return 1;
    }

    char *caminho_saida = argv[argc - 1];

    common_api_init();

    int iterations = 1000;
    float alpha = 0.2f;

    // Gera a serie sintetica: sin(i * 0.1) * 10 + (i % 7)
    float *series = (float *)malloc(sizeof(float) * iterations);
    for (int i = 0; i < iterations; i++) {
        series[i] = fadd(fmul(sinf(i * 0.1f), 10.0f), (float)(i % 7));
    }

    float ema = series[0];

    float weighted_new = 0.0f;
    float weighted_old = 0.0f;

    // series[0] entra no historico como o valor inicial da EMA
    common_api_history_push_number((double)ema);

    for (int i = 1; i < iterations; i++) {

        float x_val = series[i];

        common_api_history_increment("scale_new");
        weighted_new = fmul(alpha, x_val);

        common_api_history_increment("scale_old");
        weighted_old = fmul(fsub(1.0f, alpha), ema);

        common_api_history_increment("combine");
        ema = fadd(weighted_new, weighted_old);

        common_api_history_push_number((double)ema);
    }

    common_api_set_final_value((double)ema);
    common_api_metadata_set_number("ema", (double)ema);
    common_api_metadata_set_number("alpha", (double)alpha);

    common_api_output(caminho_saida);

    common_api_free();
    free(series);

    return 0;
}