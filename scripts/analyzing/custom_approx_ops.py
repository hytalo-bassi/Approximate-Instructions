from . import f32_approx as sf


def s_add(a, b, approx=False):
    return sf.f32_addx(a, b) if approx else a + b


def s_sub(a, b, approx=False):
    return sf.f32_subx(a, b) if approx else a - b


def s_mul(a, b, approx=False):
    return sf.f32_mulx(a, b) if approx else a * b


def s_div(a, b, approx=False):
    return a / b