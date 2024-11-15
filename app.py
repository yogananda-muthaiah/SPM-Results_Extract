from dash import Dash, dash_table, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from io import StringIO
import pandas as pd
import requests
import base64
from requests.exceptions import HTTPError
import json
import os

# Initialize the Dash app
app = Dash(__name__,
           external_stylesheets=[
               'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css',
               'https://codepen.io/chriddyp/pen/bWLwgP.css',
               'https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css',
               'https://codepen.io/chriddyp/pen/bWLwgP.css'
           ],
           meta_tags=[
               {"name": "viewport", "content": "width=device-width, initial-scale=1"},
               {'name': 'description', 'content': 'SPM ANALYTICAL APP'},
               {'property': 'og:title', 'content': 'SPM'},
               {'property': 'og:type', 'content': 'website'},
               {'property': 'og:url', 'content': ''},
               {'property': 'og:image', 'content': ''},
               {'property': 'og:image:secure_url', 'content': ''},
               {'property': 'og:image:type', 'content': 'image/png'},
               {'http-equiv': 'X-UA-Compatible', 'content': 'IE=edge'},
               {'name': "author", 'content': "Yogananda Muthaiha"},
               {'charset': "UTF-8"},
           ]
           )
app.title = 'Results Extraction UI'
cf_port = os.getenv("PORT")

# Navbar layout
navbar_layout = dbc.Navbar([
    html.A(
        dbc.Row([
            dbc.Col(html.Img(src=app.get_asset_url("SAPLogo.svg"), height="40px", style={'stroke': '#508caf'})),
            dbc.Col(dbc.NavbarBrand("SPM Incentive Management Pipeline Calculation Results Table", className="ml-2",
                                    style={'fontSize': '1.6em', 'font-family': 'sans-serif', 'fontWeight': '100', 'color': '#00000'})),
        ], align="left"), href='#'),
], sticky="top", className='mb-4 bg-white', style={'WebkitBoxShadow': '0px 5px 5px 0px rgba(100, 100, 100, 0.1)'})

# Input form layout
enterinput = html.Div([
    html.Div([
        "Tenant Name: ",
        dcc.Input(id="input5", type="text", placeholder="", style={'marginRight': '20px', 'width': '100px'}),
        "UserName: ",
        dcc.Input(id="input3", type="text", placeholder="", style={'marginRight': '10px', 'width': '18%'}),
        "Password: ",
        dcc.Input(id="input4", type="password", placeholder="", debounce=True, style={"margin-left": "15px"})
    ]),
    html.Br(),
    html.Div([
        "Enter Payee Id: ",
        dcc.Input(id="input1", type="text", placeholder="", style={'marginRight': '10px'}),
        "Enter month: ",
        dcc.Input(id="input2", type="text", placeholder="", style={'marginRight': '10px'}),
        html.Button(id='submit-button', type='submit', children='Submit',
                    style={"margin-left": "15px", "background-color": "#007bff", "color": "white"}),
    ]),
    html.Hr(style={'size': '50', 'borderColor': 'black', 'borderHeight': "10vh", "width": "100%"}),
    html.Div(id='output'),
])

# Callback to update output
@app.callback(
    Output("output", "children"),
    Input('submit-button', 'n_clicks'),
    State("input1", "value"),
    State("input2", "value"),
    State("input3", "value"),
    State("input4", "value"),
    State("input5", "value")
)
def update_output_div(clicks, payee_id, month, username, password, tenant_name):
    if clicks is not None:
        usr_pass = f"{username}:{password}"
        b64_val = base64.b64encode(usr_pass.encode()).decode()
        print(f"Tenant: {tenant_name}, Username: {usr_pass}, Base64: {b64_val}")
        api_domain = f"https://{tenant_name}.callidusondemand.com/api/v2/"
        result_tables = ["credits?", 'measurements?', 'incentives?', 'commissions?', 'deposits?']
        filter_query = f"&$filter=payee/payeeId eq '{payee_id}' and period/name eq '{month}'"
        expand_query = "expand=payee,position,period"
        select_query = "&select=payee,period,position,pipelineRunDate,name,value"
        skip_query = "&skip=0&top=100"
        count_query = "&inlineCount=true"
        sort_query = "&orderBy=pipelineRunDate asc"
        headers = {'authorization': f"Basic {b64_val}", 'Content-Type': "application/json", 'Accept': "application/json"}

        data_dict = {}
        try:
            for table in result_tables:
                table_name = table.replace("?", "")
                response = requests.get(f"{api_domain}{table}{expand_query}{filter_query}{select_query}{skip_query}{sort_query}{count_query}", headers=headers)
                response.raise_for_status()
                data_dict[table_name] = json.dumps(response.json()[table_name])
        except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
        except Exception as err:
            print(f'Other error occurred: {err}')

        # Process the data
        data_frames = [pd.read_json(StringIO(data_dict[table])) for table in ['credits', 'measurements', 'incentives', 'commissions', 'deposits']]
        combined_df = pd.concat(data_frames, ignore_index=True)

        # Normalize and clean data
        combined_df['PayeeId'] = pd.json_normalize(combined_df['payee'])['displayName']
        combined_df['Position'] = pd.json_normalize(combined_df['position'])['displayName']
        combined_df['Period'] = pd.json_normalize(combined_df['period'])['displayName']
        combined_df[['value', 'Currency']] = pd.json_normalize(combined_df['value'])[['value', 'unitType.name']]
        combined_df['pipelineRunDate'] = combined_df['pipelineRunDate'].str[:10]

        # Select relevant columns
        df_columns = ['PayeeId', 'Position', 'Period', 'pipelineRunDate', 'name', 'value', 'Currency']
        combined_df = combined_df[df_columns]

        # Return data table
        data = combined_df.to_dict('records')
        return dash_table.DataTable(data=data, export_format="csv", page_size=10, style_cell={'textAlign': 'left'})

# App layout
app.layout = html.Div([
    navbar_layout,
    enterinput
])

# Run the app
port = int(os.getenv("PORT", 0))
if __name__ == '__main__':
    if port != 0:
        app.run(host='0.0.0.0', port=cf_port)
    else:
        app.run(debug=True)