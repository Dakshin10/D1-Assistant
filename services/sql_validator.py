DANGEROUS_KEYWORDS = [
    "DROP",
    "DELETE",
    "ALTER",
    "TRUNCATE",
    "ATTACH",
    "DETACH",
    "UPDATE"
]


def needs_approval(sql):

    sql_upper = sql.upper()

    for keyword in DANGEROUS_KEYWORDS:
        if keyword in sql_upper:
            return True

    return False