import re

# Input and Output files
mysql_dump_file = "mysql_dump.sql"
postgresql_dump_file = "postgresql_dump.sql"


def convert_mysql_to_postgresql(mysql_file, postgres_file):
    with open(mysql_file, "r", encoding="utf-8") as infile:
        mysql_sql = infile.read()

    # Basic conversions
    postgres_sql = mysql_sql

    # Replace backticks (`) with double quotes (") for identifiers
    postgres_sql = postgres_sql.replace("`", '"')

    # Convert AUTO_INCREMENT to SERIAL
    postgres_sql = re.sub(r"\bAUTO_INCREMENT\b", "", postgres_sql, flags=re.IGNORECASE)

    # Convert ENGINE settings
    postgres_sql = re.sub(r"ENGINE=\w+\s*", "", postgres_sql, flags=re.IGNORECASE)
    postgres_sql = re.sub(r"DEFAULT CHARSET=\w+\s*", "", postgres_sql, flags=re.IGNORECASE)

    # Replace unsigned integers (PostgreSQL does not have unsigned ints)
    postgres_sql = re.sub(r"\bunsigned\b", "", postgres_sql, flags=re.IGNORECASE)

    # Convert tinyint(1) to BOOLEAN
    postgres_sql = re.sub(r"\btinyint\(1\)", "BOOLEAN", postgres_sql, flags=re.IGNORECASE)

    # Remove COMMENTs in table definitions
    postgres_sql = re.sub(r"COMMENT\s+\'[^\']*\'", "", postgres_sql, flags=re.IGNORECASE)

    # Replace "int(x)" types with just "INTEGER"
    postgres_sql = re.sub(r"\bint\(\d+\)", "INTEGER", postgres_sql, flags=re.IGNORECASE)

    # Replace "double" with "DOUBLE PRECISION"
    postgres_sql = re.sub(r"\bdouble\b", "DOUBLE PRECISION", postgres_sql, flags=re.IGNORECASE)

    # Replace "bool" with "BOOLEAN"
    postgres_sql = re.sub(r"\bbool\b", "BOOLEAN", postgres_sql, flags=re.IGNORECASE)

    # Replace "datetime" with "TIMESTAMP"
    postgres_sql = re.sub(r"\bdatetime\b", "TIMESTAMP", postgres_sql, flags=re.IGNORECASE)

    # Optional: Remove DEFINER statements if they exist
    postgres_sql = re.sub(r"DEFINER=[^*]*\*", "", postgres_sql, flags=re.IGNORECASE)

    # Optional: Remove SET statements (MySQL-specific settings)
    postgres_sql = re.sub(r"SET\s+\w+\s*=\s*[^;]+;", "", postgres_sql, flags=re.IGNORECASE)

    with open(postgres_file, "w", encoding="utf-8") as outfile:
        outfile.write(postgres_sql)

    print(f"Conversion complete! PostgreSQL file created: {postgres_file}")


if __name__ == "__main__":
    convert_mysql_to_postgresql(mysql_dump_file, postgresql_dump_file)
