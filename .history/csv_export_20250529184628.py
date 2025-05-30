import io
import pandas as pd
from flask import Response

@app.route("/v1/export/<kind>", methods=["GET"])
def export_csv(kind: str):
    if kind not in {"stocks", "sales", "logs"}:
        return error_response()

    if kind == "stocks":
        rows = query_all("SELECT name, amount FROM stocks ORDER BY name")
        df = pd.DataFrame(rows, columns=["name", "amount"])
    elif kind == "sales":
        total = query_one("SELECT total FROM sales WHERE id=1")[0]
        df = pd.DataFrame([{"sales": ceil_two_decimals(total)}])
    else:  # logs
        rows = query_all(
            "SELECT name, action, amount, timestamp FROM logs ORDER BY id DESC"
        )
        df = pd.DataFrame(rows, columns=["name", "action", "amount", "timestamp"])

    buf = io.StringIO()
    df.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode()
    return Response(
        csv_bytes,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{kind}.csv"'},
    )