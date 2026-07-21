"""
Algoritmo de regressão linear treinada com Gradiente Descendente + RMSProp,
usando os wrappers s_add/s_sub/s_mul/s_div para tornar cada operação
endereçável (approx ligado/desligado individualmente).
"""

import math
from analyzing.custom_approx_ops import s_add, s_sub, s_mul, s_div
from analyzing.scoring import ExecutionResult

DADOS = [
    (1.0, 2.5), (2.0, 4.8), (3.0, 5.9), (4.0, 7.5), (5.0, 5.0),
]
N = len(DADOS)
X_REF = sum(x for x, _ in DADOS) / N 


def sgd_linear_regression(epochs, bits):
    """
    bits: dict indexado pelo nome da op (ver .ops abaixo), ex.:
          {"mul_pred": True, "update_m": True, ...}
    Chaves ausentes default para False (exato) via bits.get(...).
    """
    m = 0.0
    b = 0.0
    learning_rate = 0.03
    beta = 0.9
    epsilon = 1e-8

    v_m = 0.0
    v_b = 0.0

    history = []
    execution_count = {op: 0 for op in sgd_linear_regression.ops}

    for _ in range(epochs):
        grad_m_total = 0.0
        grad_b_total = 0.0

        for x_val, y_val in DADOS:
            execution_count["mul_pred"] += 1
            componente_x = s_mul(m, x_val, bits.get("mul_pred", False))

            execution_count["add_pred"] += 1
            previsao = s_add(componente_x, b, bits.get("add_pred", False))

            execution_count["sub_error"] += 1
            erro = s_sub(y_val, previsao, bits.get("sub_error", False))

            # grad_m = 2 * x_val * erro — as duas multiplicações compartilham o mesmo bit
            execution_count["mul_grad_m"] += 1
            gm_parcial = s_mul(2.0, x_val, bits.get("mul_grad_m", False))
            grad_m = s_mul(gm_parcial, erro, bits.get("mul_grad_m", False))

            execution_count["mul_grad_b"] += 1
            grad_b = s_mul(2.0, erro, bits.get("mul_grad_b", False))

            execution_count["sub_accum_gm"] += 1
            grad_m_total = s_sub(grad_m_total, grad_m, bits.get("sub_accum_gm", False))

            execution_count["sub_accum_gb"] += 1
            grad_b_total = s_sub(grad_b_total, grad_b, bits.get("sub_accum_gb", False))

        execution_count["div_mean_gm"] += 1
        grad_m_total = s_div(grad_m_total, float(N), bits.get("div_mean_gm", False))

        execution_count["div_mean_gb"] += 1
        grad_b_total = s_div(grad_b_total, float(N), bits.get("div_mean_gb", False))

        # v = beta*v + (1-beta)*grad^2 — três operações, um único bit por variável
        execution_count["update_vm"] += 1
        vm_a = s_mul(beta, v_m, bits.get("update_vm", False))
        vm_b = s_mul(grad_m_total, grad_m_total, bits.get("update_vm", False))
        vm_c = s_mul(1.0 - beta, vm_b, bits.get("update_vm", False))
        v_m = s_add(vm_a, vm_c, bits.get("update_vm", False))

        execution_count["update_vb"] += 1
        vb_a = s_mul(beta, v_b, bits.get("update_vb", False))
        vb_b = s_mul(grad_b_total, grad_b_total, bits.get("update_vb", False))
        vb_c = s_mul(1.0 - beta, vb_b, bits.get("update_vb", False))
        v_b = s_add(vb_a, vb_c, bits.get("update_vb", False))

        # sqrt fica exato (sem s_sqrt); só a divisão final é endereçável
        execution_count["div_lr_m"] += 1
        adaptive_lr_m = s_div(learning_rate, math.sqrt(v_m) + epsilon, bits.get("div_lr_m", False))

        execution_count["div_lr_b"] += 1
        adaptive_lr_b = s_div(learning_rate, math.sqrt(v_b) + epsilon, bits.get("div_lr_b", False))

        # m -= adaptive_lr_m * grad_m_total — mul + sub compartilham o mesmo bit
        execution_count["update_m"] += 1
        delta_m = s_mul(adaptive_lr_m, grad_m_total, bits.get("update_m", False))
        m = s_sub(m, delta_m, bits.get("update_m", False))

        execution_count["update_b"] += 1
        delta_b = s_mul(adaptive_lr_b, grad_b_total, bits.get("update_b", False))
        b = s_sub(b, delta_b, bits.get("update_b", False))

        history.append(m * X_REF + b)

    final_value = m * X_REF + b

    return ExecutionResult(
        final_value=final_value,
        history=history,
        execution_count=execution_count,
        metadata={
            "a": m,
            "b": b,
            "graph_type": "line",
            "data_points": DADOS,
        }
    )


sgd_linear_regression.ops = (
    "mul_pred", "add_pred", "sub_error",
    "mul_grad_m", "mul_grad_b",
    "sub_accum_gm", "sub_accum_gb",
    "div_mean_gm", "div_mean_gb",
    "update_vm", "update_vb",
    "div_lr_m", "div_lr_b",
    "update_m", "update_b",
)