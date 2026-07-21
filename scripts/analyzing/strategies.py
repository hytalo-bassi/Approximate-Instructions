import random
import itertools
import math
from analyzing.scoring import evaluate_candidate


def dedupe_candidates(results):
    """Drop results with a bit-pattern already seen, keeping the first occurrence."""
    seen = set()
    deduped = []
    for r in results:
        key = tuple(sorted(r["bits"].items()))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


def vector_to_bits(vector, op_names):
    return {op: bool(v) for op, v in zip(op_names, vector)}


def bits_to_vector(bits, op_names):
    return [1 if bits[op] else 0 for op in op_names]


def random_strategy(fn, iterations, op_names, n_samples=20, seed=None, **kwargs):
    rng = random.Random(seed)
    results = []
    for _ in range(n_samples):
        bits = {op: rng.random() < 0.5 for op in op_names}
        results.append(evaluate_candidate(fn, iterations, bits))
    return results


def sweep_strategy(fn, iterations, op_names, **kwargs):
    candidates = [dict(zip(op_names, combo)) for combo in itertools.product([False, True], repeat=len(op_names))]
    return [evaluate_candidate(fn, iterations, bits) for bits in candidates]


def nsga2_strategy(fn, iterations, op_names, pop_size=20, generations=20,
                    mutation_rate=None, objectives_fn=None, seed=None, **kwargs):
    """
    Returns the final Pareto front: candidates where no other candidate found
    is strictly better in every objective. Use this when the search space
    (number of ops) is too large to sweep exhaustively, or when you want a
    tradeoff curve (error vs. approx-count) instead of one "best" answer.
    """
    rng = random.Random(seed)
    objectives_fn = objectives_fn or default_objectives
    mutation_rate = mutation_rate if mutation_rate is not None else 1.0 / len(op_names)
    n_genes = len(op_names)
 
    def make_individual():
        return [rng.randint(0, 1) for _ in range(n_genes)]
 
    def evaluate(vector):
        bits = vector_to_bits(vector, op_names)
        result = evaluate_candidate(fn, iterations, bits)
        return result, objectives_fn(result)
 
    population = [make_individual() for _ in range(pop_size)]
    evaluated = [evaluate(ind) for ind in population]
 
    for _ in range(generations):
        objs = [obj for _, obj in evaluated]
        viols = [_violation(res) for res, _ in evaluated]
        fronts = _fast_non_dominated_sort(objs, viols)
        ranks = [0] * len(population)
        distances = [0.0] * len(population)
        for rank, front in enumerate(fronts):
            crowd = _crowding_distance(objs, front)
            for i in front:
                ranks[i] = rank
                distances[i] = crowd[i]
 
        offspring = []
        while len(offspring) < pop_size:
            p1 = _tournament_select(population, ranks, distances, rng)
            p2 = _tournament_select(population, ranks, distances, rng)
            child = _mutate(_crossover(p1, p2, rng), mutation_rate, rng)
            offspring.append(child)
        offspring_evaluated = [evaluate(ind) for ind in offspring]
 
        combined_pop = population + offspring
        combined_eval = evaluated + offspring_evaluated
        combined_obj = [obj for _, obj in combined_eval]
        combined_viol = [_violation(res) for res, _ in combined_eval]
        fronts = _fast_non_dominated_sort(combined_obj, combined_viol)
 
        new_population, new_evaluated = [], []
        for front in fronts:
            if len(new_population) + len(front) <= pop_size:
                new_population.extend(combined_pop[i] for i in front)
                new_evaluated.extend(combined_eval[i] for i in front)
            else:
                crowd = _crowding_distance(combined_obj, front)
                remaining = pop_size - len(new_population)
                chosen = sorted(front, key=lambda i: -crowd[i])[:remaining]
                new_population.extend(combined_pop[i] for i in chosen)
                new_evaluated.extend(combined_eval[i] for i in chosen)
                break
        population, evaluated = new_population, new_evaluated
 
    final_obj = [obj for _, obj in evaluated]
    final_viol = [_violation(res) for res, _ in evaluated]
    pareto_indices = _fast_non_dominated_sort(final_obj, final_viol)[0]
    pareto = [evaluated[i][0] for i in pareto_indices]
    return dedupe_candidates(pareto)


def default_objectives(result):
    approx_count = sum(result["bits"].values())
    return (result["global_error"], -approx_count)
 
 
def _dominates(obj_a, obj_b):
    not_worse = all(a <= b for a, b in zip(obj_a, obj_b))
    strictly_better = any(a < b for a, b in zip(obj_a, obj_b))
    return not_worse and strictly_better
 
 
def _violation(result):
    """0.0 for a usable (finite-error) candidate; 1.0 for a diverged one.
    Without this, a diverged candidate can still look "non-dominated" just
    by approximating more ops (winning on that objective alone) even
    though its result is unusable. Constrained-domination below makes any
    feasible candidate beat any infeasible one outright, regardless of
    approx-count — standard practice for handling invalid solutions in
    multi-objective search."""
    return 0.0 if math.isfinite(result["global_error"]) else 1.0
 
 
def _dominates_constrained(obj_a, violation_a, obj_b, violation_b):
    if violation_a > 0 or violation_b > 0:
        return violation_a < violation_b
    return _dominates(obj_a, obj_b)
 
 
def _fast_non_dominated_sort(objectives, violations=None):
    n = len(objectives)
    if violations is None:
        violations = [0.0] * n
    dominated_by = [set() for _ in range(n)]
    domination_count = [0] * n
    fronts = [[]]
    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if _dominates_constrained(objectives[p], violations[p], objectives[q], violations[q]):
                dominated_by[p].add(q)
            elif _dominates_constrained(objectives[q], violations[q], objectives[p], violations[p]):
                domination_count[p] += 1
        if domination_count[p] == 0:
            fronts[0].append(p)
    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in dominated_by[p]:
                domination_count[q] -= 1
                if domination_count[q] == 0:
                    next_front.append(q)
        i += 1
        fronts.append(next_front)
    fronts.pop()
    return fronts
 
 
def _crowding_distance(objectives, front):
    distance = {i: 0.0 for i in front}
    if len(front) <= 2:
        for i in front:
            distance[i] = float("inf")
        return distance
    num_obj = len(objectives[0])
    for m in range(num_obj):
        front_sorted = sorted(front, key=lambda i: objectives[i][m])
        distance[front_sorted[0]] = float("inf")
        distance[front_sorted[-1]] = float("inf")
        min_val = objectives[front_sorted[0]][m]
        max_val = objectives[front_sorted[-1]][m]
        if max_val == min_val:
            continue
        for k in range(1, len(front_sorted) - 1):
            prev_val = objectives[front_sorted[k - 1]][m]
            next_val = objectives[front_sorted[k + 1]][m]
            distance[front_sorted[k]] += (next_val - prev_val) / (max_val - min_val)
    return distance
 
 
def _tournament_select(pop, ranks, distances, rng):
    i, j = rng.randrange(len(pop)), rng.randrange(len(pop))
    if ranks[i] != ranks[j]:
        return pop[i] if ranks[i] < ranks[j] else pop[j]
    return pop[i] if distances[i] >= distances[j] else pop[j]
 
 
def _crossover(parent_a, parent_b, rng):
    return [a if rng.random() < 0.5 else b for a, b in zip(parent_a, parent_b)]
 
 
def _mutate(vector, mutation_rate, rng):
    return [1 - v if rng.random() < mutation_rate else v for v in vector]
 