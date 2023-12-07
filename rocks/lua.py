import lupa.lua52 as lupa


lua_type = lupa.lua_type
interpretator = lupa.LuaRuntime()


def table2dict(t) -> dict:
    if lua_type(t) != "table":
        raise Exception("not a lua table")

    data = {}
    for k, v in t.items():
        if lua_type(v) == "table":
            data[k] = table2dict(v)
        else:
            data[k] = v

    return data
