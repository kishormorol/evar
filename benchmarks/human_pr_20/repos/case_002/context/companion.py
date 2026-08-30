Original path: tests/data/cases/skip_magic_trailing_comma.py
Snapshot commit: 006b2a74d4deac01fa16e85ccc9f5810b53a7391
Original lines: 34-82

    three,
).four(
    five,
)

func1(arg1).func2(arg2,).func3(arg3).func4(arg4,).func5(arg5)

(
    a,
    b,
    c,
    d,
) = func1(
    arg1
) and func2(arg2)

func(
    argument1,
    (
        one,
        two,
    ),
    argument4,
    argument5,
    argument6,
)

# Also keep it when the line is long enough to be split and a power operator
# sends it through hug_power_op, which used to rebuild the line from leaves that
# had lost their place in the tree.
value = alpha[beta,]() ** gamma * delta << epsilon | zeta < eta ^ theta * iota + kappa + mu

# output
# We should not remove the trailing comma in a single-element subscript.
a: tuple[int,]
b = tuple[int,]

# But commas in multiple element subscripts should be removed.
c: tuple[int, int]
d = tuple[int, int]

# Remove commas for non-subscripts.
small_list = [1]
list_of_types = [tuple[int,]]
small_set = {1}
set_of_types = {tuple[int,]}

# Except single element tuples
small_tuple = (1,)
