from ortools.sat.python import cp_model
import matplotlib.pyplot as plt
import networkx as nx
from random import uniform

# Define the data
L = 10
num_cities = 25
days = range(5)
time_slots_per_day = list(range(8, 18))
cities = range(num_cities)
starting_city = 0

fixed_destionations = [{"id": 1, "day": 0, "time": 10}, {"id": 2, "day": 1, "time": 14}]
semi_fixed_destinations = [
    {"id": 3, "options": [(0, 11), (2, 10), (1, 10)]},
    {"id": 4, "options": [(2, 15), (3, 13), (4, 12)]},
]
free_destinations = [
    {"id": 5},
    {"id": 6},
]
distance_matrix = [
    # Matrix of distances between destinations
    # (This should be populated based on actual distances between the points)
    [0, 10, 15, 20, 25, 30],
    [10, 0, 35, 25, 30, 15],
    [15, 35, 0, 30, 20, 10],
    [20, 25, 30, 0, 15, 25],
    [25, 30, 20, 15, 0, 20],
    [30, 15, 10, 25, 20, 0],
]
n = len(distance_matrix)


# Create the model
model = cp_model.CpModel()

free_vars = {}
for destination in free_destinations:
    day_var = model.NewIntVar(0, len(days) - 1, f"day_{destination['id']}")
    time_var = model.NewIntVar(
        min(time_slots_per_day), max(time_slots_per_day), f"time_{destination['id']}"
    )
    free_vars[destination["id"]] = (day_var, time_var)

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

# for day in days:
#     model.Add(
#         sum(tsp_vars[(starting_city, j, day)] for j in range(1, n)) == 1
#     )  # Start from depot
#     model.Add(sum(tsp_vars[(i, starting_city, day)] for i in range(1, n)) == 1)

# Subtour elimination (Lazy constraints could be used here for large problems)
# A simplified approach using a "big-M" method
# for day in days:
#     u = [model.NewIntVar(0, n - 1, f"u_{i}_day_{day}") for i in range(n)]
#     for i in range(1, n):
#         for j in range(1, n):
#             if i != j:
#                 model.Add(u[i] - u[j] + (n - 1) * tsp_vars[(i, j, day)] <= n - 2)

# for i in range(1, n):
#     model.Add(
#         sum(tsp_vars[(i, j, day)] for day in days for j in range(n) if i != j) == 1
#     )
#     model.Add(
#         sum(tsp_vars[(j, i, day)] for day in days for j in range(n) if i != j) == 1
#     )


# Link TSP route choices with scheduling (i.e., only allow routes on selected days)
for day in days:
    for i in range(n):  # not considering depot
        for j in range(n):  # not considering depot
            if i != j:
                pass
                # Link with free destinations
                # if i in free_vars:
                #     day_var = model.NewBoolVar(f"day_var_{i}_{day}")
                #     model.Add(free_vars[i][0] == day).OnlyEnforceIf(day_var)

                #     model.Add(tsp_vars[(i, j, day)] == 1).OnlyEnforceIf(day_var)
                #     model.Add(tsp_vars[(i, j, day)] == 0).OnlyEnforceIf(day_var.Not())

                # if j in free_vars:
                #     day_var = model.NewBoolVar(f"day_var_{j}_{day}")
                #     model.Add(free_vars[j][0] == day).OnlyEnforceIf(day_var)

                #     model.Add(tsp_vars[(i, j, day)] == 1).OnlyEnforceIf(day_var)
                #     model.Add(tsp_vars[(i, j, day)] == 0).OnlyEnforceIf(day_var.Not())

                # Link with semi-fixed destinations
                for option_index, (option_day, _) in enumerate(
                    semi_fixed_destinations[0]["options"]
                ):
                    if i in semi_fixed_vars.keys():
                        if option_day == day:
                            model.Add(tsp_vars[(i, j, day)] == 1).OnlyEnforceIf(
                                semi_fixed_vars[i][option_index]
                            )
                        else:
                            model.Add(tsp_vars[(i, j, option_day)] == 0).OnlyEnforceIf(
                                semi_fixed_vars[i][option_index].Not()
                            )
                    if j in semi_fixed_vars.keys():
                        if option_day == day:
                            model.Add(tsp_vars[(i, j, day)] == 1).OnlyEnforceIf(
                                semi_fixed_vars[j][option_index]
                            )
                        else:
                            model.Add(tsp_vars[(i, j, option_day)] == 0).OnlyEnforceIf(
                                semi_fixed_vars[j][option_index].Not()
                            )

# Objective: Minimize total travel distance across all days
model.Minimize(
    sum(
        distance_matrix[i][j] * tsp_vars[(i, j, day)]
        for day in days
        for i in range(n)
        for j in range(n)
        if i != j
    )
)

# Solve the model
solver = cp_model.CpSolver()
status = solver.Solve(model)

# Output the result
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print("Solution found:")

    # Print the assignments for free destinations
    for free_id, (day_var, time_var) in free_vars.items():
        print(
            f"Free Destination {free_id}: Day {solver.Value(day_var)}, Time {solver.Value(time_var)}"
        )

        # Print the assignments for semi-fixed destinations
    for semi_id, option_vars in semi_fixed_vars.items():
        chosen_option = [i for i, var in enumerate(option_vars) if solver.Value(var)]
        if chosen_option:
            day, time = [i for i in semi_fixed_destinations if semi_id == i["id"]][0][
                "options"
            ][chosen_option[0]]
            print(f"Semi-Fixed Destination {semi_id}: Day {day}, Time {time}")

    # Visualize the solution
    G = nx.Graph()
    G.add_nodes_from(range(n))
    routes = []

    # Print the TSP routes
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
