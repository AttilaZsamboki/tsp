from ortools.sat.python import cp_model
import matplotlib.pyplot as plt
import networkx as nx
import random

# Define the data
days = range(10)
num_cities = 15
time_slots_per_day = list(range(8, 18))
starting_city = 0

fixed_destionations = [{"id": 1, "day": 0, "time": 10}, {"id": 2, "day": 1, "time": 14}]
semi_fixed_destinations = [
    {"id": 3, "options": [(0, 11), (2, 10), (1, 10)]},
    {"id": 4, "options": [(2, 15), (3, 13), (4, 12)]},
    {"id": 7, "options": [(5, 8), (1, 13), (0, 12)]},
    {"id": 9, "options": [(6, 12), (2, 15), (2, 14)]},
    {"id": 13, "options": [(7, 11), (9, 8), (2, 15)]},
]
free_destinations = [
    {"id": 5},
    {"id": 6},
    {"id": 8},
    {"id": 11},
    {"id": 12},
    {"id": 14},
]

distance_matrix = []
for i in range(num_cities):
    row = []
    for j in range(num_cities):
        if i == j:
            row.append(0)
        else:
            row.append(random.randint(1, 100))
    distance_matrix.append(row)

n = len(distance_matrix)


model = cp_model.CpModel()

free_vars = {}
for destination in free_destinations:
    day_var = model.NewIntVar(0, len(days) - 1, f"day_{destination['id']}")
    time_var = model.NewIntVar(
        min(time_slots_per_day), max(time_slots_per_day), f"time_{destination['id']}"
    )
    free_vars[destination["id"]] = (day_var, time_var)

semi_fixed_slack = model.NewBoolVar("semi_fixed_slack")

semi_fixed_vars = {}
for destination in semi_fixed_destinations:
    option_vars = []
    for option in destination["options"]:
        day, time = option
        var = model.NewBoolVar(f"option_{destination['id']}_{day}_{time}")
        option_vars.append(var)
    semi_fixed_vars[destination["id"]] = option_vars

    model.Add(sum(option_vars) == 1)

for destination in fixed_destionations:
    free_vars[destination["id"]] = (
        model.NewConstant(destination["day"]),
        model.NewConstant(destination["time"]),
    )
    model.Add(free_vars[destination["id"]][0] == destination["day"])
    model.Add(free_vars[destination["id"]][1] == destination["time"])


for day in days:
    for time in time_slots_per_day:
        overlapping = []

        for free_id, (day_var, time_var) in free_vars.items():
            is_scheduled = model.NewBoolVar(
                f"overlap_day_{day}_time_{time}_free_{free_id}"
            )
            overlapping.append(is_scheduled)

            time_diff = model.NewBoolVar("time_diff")
            day_diff = model.NewBoolVar("day_diff")

            # Enforce the relationship between the variables and the inequalities
            model.Add(time_var != time).OnlyEnforceIf(time_diff.Not())
            model.Add(time_var == time).OnlyEnforceIf(time_diff)

            model.Add(day_var != day).OnlyEnforceIf(day_diff.Not())
            model.Add(day_var == day).OnlyEnforceIf(day_diff)

            # Use the boolean variables in the AddBoolOr constraint
            model.AddBoolOr([time_diff, day_diff]).OnlyEnforceIf(is_scheduled)
            model.AddBoolOr([time_diff.Not(), day_diff.Not()]).OnlyEnforceIf(
                is_scheduled.Not()
            )

        for semi_id, option_vars in semi_fixed_vars.items():
            for option_index, (option_day, option_time) in enumerate(
                [i for i in semi_fixed_destinations if semi_id == i["id"]][0]["options"]
            ):
                if option_day == day and option_time == time:
                    overlapping.append(option_vars[option_index])

        model.Add(sum(overlapping) <= 1)

tsp_vars = {}
for day in days:
    for i in range(n):
        for j in range(n):
            if i != j:
                tsp_vars[(i, j, day)] = model.NewBoolVar(f"tsp_{i}_{j}_day_{day}")

for day in days:
    condition_var = model.NewBoolVar(f"condition_var_{day}")
    trips_planned = sum(
        tsp_vars[(i, j, day)] for i in range(n) for j in range(n) if i != j
    )

    model.Add(trips_planned >= 1).OnlyEnforceIf(condition_var)
    model.Add(trips_planned == 0).OnlyEnforceIf(condition_var.Not())

    model.Add(
        sum(tsp_vars[(starting_city, j, day)] for j in range(1, n)) == 1
    ).OnlyEnforceIf(condition_var)
    model.Add(
        sum(tsp_vars[(j, starting_city, day)] for j in range(1, n)) == 1
    ).OnlyEnforceIf(condition_var)

for day in days:
    u = [model.NewIntVar(0, n - 1, f"u_{i}_day_{day}") for i in range(n)]
    for i in range(1, n):
        for j in range(1, n):
            if i != j:
                model.Add(u[i] - u[j] + (n - 1) * tsp_vars[(i, j, day)] <= n - 2)

for i in range(1, n):
    model.Add(
        sum(tsp_vars[(i, j, day)] for day in days for j in range(n) if i != j) == 1
    )
    model.Add(
        sum(tsp_vars[(j, i, day)] for day in days for j in range(n) if i != j) == 1
    )


for day in days:
    for i in range(n):
        for j in range(n):
            if i != j:
                if i in free_vars.keys():
                    day_var = model.NewBoolVar(f"day_var_{i}_{day}")
                    model.Add(free_vars[i][0] == day).OnlyEnforceIf(day_var)

                    model.Add(tsp_vars[(i, j, day)] == 1).OnlyEnforceIf(day_var)
                    model.Add(tsp_vars[(i, j, day)] == 0).OnlyEnforceIf(day_var.Not())

                if j in free_vars.keys():
                    day_var2 = model.NewBoolVar(f"day_var_{j}_{day}")
                    model.Add(free_vars[j][0] == day).OnlyEnforceIf(day_var2)

                    model.Add(tsp_vars[(i, j, day)] == 1).OnlyEnforceIf(day_var2)
                    model.Add(tsp_vars[(i, j, day)] == 0).OnlyEnforceIf(day_var2.Not())

                if i in semi_fixed_vars:
                    for option_index, (option_day, _) in enumerate(
                        [t for t in semi_fixed_destinations if i == t["id"]][0][
                            "options"
                        ]
                    ):
                        if option_day == day:
                            model.Add(
                                sum(tsp_vars[(i, t, day)] for t in range(n) if i != t)
                                == 1
                            ).OnlyEnforceIf(semi_fixed_vars[i][option_index])
                            model.Add(
                                sum(tsp_vars[(t, i, day)] for t in range(n) if i != t)
                                == 1
                            ).OnlyEnforceIf(semi_fixed_vars[i][option_index])

                            model.Add(
                                sum(tsp_vars[(t, i, day)] for t in range(n) if i != t)
                                == 0
                            ).OnlyEnforceIf(semi_fixed_vars[i][option_index].Not())

for day in days:
    for i in range(n):
        for j in range(n):
            if i in free_vars.keys():
                if j in free_vars.keys():
                    if i != j:
                        model.Add(free_vars[i][1] < free_vars[j][1]).OnlyEnforceIf(
                            tsp_vars[(i, j, day)]
                        )
            for semi_id, option_vars in semi_fixed_vars.items():
                for option_index, (option_day, option_time) in enumerate(
                    [t for t in semi_fixed_destinations if semi_id == t["id"]][0][
                        "options"
                    ]
                ):
                    if option_day == day:
                        if i == semi_id:
                            if j in free_vars.keys():
                                model.Add(option_time < free_vars[j][1]).OnlyEnforceIf(
                                    option_vars[option_index]
                                ).OnlyEnforceIf(tsp_vars[(i, j, day)])
                        if j == semi_id:
                            if i in free_vars.keys():
                                model.Add(free_vars[i][1] < option_time).OnlyEnforceIf(
                                    option_vars[option_index]
                                ).OnlyEnforceIf(tsp_vars[(i, j, day)])

model.Minimize(
    sum(
        distance_matrix[i][j] * tsp_vars[(i, j, day)]
        for day in days
        for i in range(n)
        for j in range(n)
        if i != j
    )
)

solver = cp_model.CpSolver()
status = solver.Solve(model)

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print("Solution found:")

    for free_id, (day_var, time_var) in free_vars.items():
        print(
            f"Free Destination {free_id}: Day {solver.Value(day_var)}, Time {solver.Value(time_var)}"
        )

    for semi_id, option_vars in semi_fixed_vars.items():
        chosen_option = [i for i, var in enumerate(option_vars) if solver.Value(var)]
        if chosen_option:
            day, time = [i for i in semi_fixed_destinations if semi_id == i["id"]][0][
                "options"
            ][chosen_option[0]]
            print(f"Semi-Fixed Destination {semi_id}: Day {day}, Time {time}")

    G = nx.Graph()
    G.add_nodes_from(range(n))
    routes = []

    for day in days:
        print(f"Day {day} route:")
        for i in range(n):
            for j in range(n):
                if i != j and solver.Value(tsp_vars[(i, j, day)]):
                    routes.append((i, j))
                    print(f"Travel from {i} to {j}")
    G.add_edges_from(routes)
    nx.draw(G, with_labels=True)
    plt.title("Traveling Salesman Problem Solution")
    plt.show()
else:
    print("No solution found.")
