import gradio as gr
from services.sql_service import generate_sql
import pandas as pd

from services.d1_service import (
    execute_query,
    get_schema,
    get_tables,
    get_table_data
)

from services.sql_validator import needs_approval


PENDING_SQL = None


def get_dataframe_from_result(result_dict):
    if isinstance(result_dict, dict) and result_dict.get("success") and "columns" in result_dict:
        rows = result_dict["result"]
        cols = result_dict["columns"]
        df = pd.DataFrame(rows, columns=cols)
        return gr.update(value=df, visible=True)
    return gr.update(visible=False)


def process_request(prompt):

    global PENDING_SQL

    # Generate SQL using unified LangChain SQL Generation Chain
    sql = generate_sql(prompt)

    if sql.startswith("ERROR:"):
        err_res = {
            "success": False,
            "error": sql
        }
        return (
            sql,
            err_res,
            get_schema(),
            gr.update(visible=False),
            "",
            gr.update(visible=False)
        )

    if needs_approval(sql):

        PENDING_SQL = sql

        err_res = {
            "success": False,
            "message": "⚠️ Human approval required."
        }

        return (
            sql,
            err_res,
            get_schema(),
            gr.update(visible=True),
            f"""
⚠️ APPROVAL REQUIRED

Generated SQL:

{sql}

This query may modify data.
Review carefully before executing.
""",
            gr.update(visible=False)
        )

    result = execute_query(sql)
    df_update = get_dataframe_from_result(result)

    return (
        sql,
        result,
        get_schema(),
        gr.update(visible=False),
        "",
        df_update
    )


def approve_sql():

    global PENDING_SQL

    if not PENDING_SQL:

        error_res = {
            "success": False,
            "message": "No pending SQL found."
        }
        return (
            error_res,
            error_res,
            get_schema(),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False)
        )

    result = execute_query(PENDING_SQL)

    PENDING_SQL = None

    df_update = get_dataframe_from_result(result)

    return (
        result,
        result,
        get_schema(),
        gr.update(visible=False),
        df_update,
        df_update
    )


def reject_sql():

    global PENDING_SQL

    PENDING_SQL = None

    reject_res = {
        "success": False,
        "message": "❌ Query rejected by user."
    }

    return (
        reject_res,
        reject_res,
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False)
    )


def explorer(table_name):

    if not table_name:
        return pd.DataFrame()

    rows, columns = get_table_data(table_name)

    print("TABLE:", table_name)
    print("ROWS:", rows)
    print("COLUMNS:", columns)

    return pd.DataFrame(
        rows,
        columns=columns
    )


custom_css = """
#approval_modal {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background: rgba(0, 0, 0, 0.75) !important;
    z-index: 99999 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

#approval_modal.hidden,
#approval_modal.hide,
#approval_modal[hidden],
#approval_modal[style*="display: none"],
#approval_modal[style*="display:none"] {
    display: none !important;
}

#approval_modal_content {
    background-color: #1b1b2f !important;
    border: 1px solid #3d3d5c !important;
    border-radius: 12px !important;
    padding: 30px !important;
    max-width: 600px !important;
    width: 90% !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6) !important;
    margin: auto !important;
}
"""

with gr.Blocks(title="Natural Database Assistant") as app:

    gr.Markdown("# Natural Database Assistant")

    with gr.Column(elem_id="approval_modal", visible=False) as approval_modal:
        with gr.Column(elem_id="approval_modal_content"):
            gr.Markdown("### ⚠️ Human Approval Required")
            approval_warning = gr.Textbox(
                label="Query details and warning",
                lines=6,
                interactive=False
            )
            with gr.Row():
                reject_btn = gr.Button("Reject", variant="stop")
                accept_btn = gr.Button("Accept", variant="primary")

    with gr.Tab("Database Builder"):

        prompt = gr.Textbox(
            label="Create Tables / Insert Data",
            lines=5
        )

        btn = gr.Button("Generate & Execute")

        sql_output = gr.Code(
            label="Generated SQL",
            language="sql"
        )

        result_output = gr.JSON(
            label="Execution Result"
        )

        builder_dataframe = gr.Dataframe(
            label="Result Table",
            visible=False
        )

        schema_output = gr.Textbox(
            label="Current Schema",
            value=get_schema(),
            lines=10
        )

        btn.click(
            fn=process_request,
            inputs=prompt,
            outputs=[
                sql_output,
                result_output,
                schema_output,
                approval_modal,
                approval_warning,
                builder_dataframe
            ]
        )

    with gr.Tab("Query Database"):

        query_input = gr.Textbox(
            label="Ask a Question",
            lines=3
        )

        query_btn = gr.Button("Ask")

        query_sql = gr.Code(
            label="Generated SQL",
            language="sql"
        )

        query_result = gr.JSON(
            label="Result"
        )

        query_dataframe = gr.Dataframe(
            label="Result Table",
            visible=False
        )

        query_btn.click(
            fn=process_request,
            inputs=query_input,
            outputs=[
                query_sql,
                query_result,
                schema_output,
                approval_modal,
                approval_warning,
                query_dataframe
            ]
        )

    with gr.Tab("Database Explorer"):

        with gr.Row():
            table_dropdown = gr.Dropdown(
                choices=get_tables(),
                label="Select Table",
                scale=4
            )
            refresh_btn = gr.Button("🔄 Refresh Tables", scale=1)

        view_btn = gr.Button("📂 Fetch & Show Table Data", variant="primary")

        table_data = gr.Dataframe(
            label="Table Contents"
        )

        def refresh_tables():
            return gr.update(choices=get_tables())

        refresh_btn.click(
            fn=refresh_tables,
            outputs=table_dropdown
        )

        table_dropdown.focus(
            fn=refresh_tables,
            outputs=table_dropdown
        )

        view_btn.click(
            fn=explorer,
            inputs=table_dropdown,
            outputs=table_data
        )

    accept_btn.click(
        fn=approve_sql,
        outputs=[
            result_output,
            query_result,
            schema_output,
            approval_modal,
            builder_dataframe,
            query_dataframe
        ]
    )

    reject_btn.click(
        fn=reject_sql,
        outputs=[
            result_output,
            query_result,
            approval_modal,
            builder_dataframe,
            query_dataframe
        ]
    )

if __name__ == "__main__":
    app.launch(css=custom_css)