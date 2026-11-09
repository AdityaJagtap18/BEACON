import warnings
warnings.filterwarnings('ignore')
import os
import sys
import secrets

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
 
from quart import Quart, flash, jsonify, redirect, render_template, request, send_file, session, url_for,Response
from plotly import graph_objects as go
from datetime import datetime, timedelta
from src.utility import *
from src.functions import *
import asyncio
import time
import os

# User data for Demonstration
# USERS = users.get("users")

USERS               = load_user_info().get("Users")#{"admin": "1234"}
log_file            = create_log_files(user_name="admin")

current_date = str(datetime.now()).split(" ")[0]

# Application Configrations
app = Quart(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(24))

UPLOAD_FOLDER = "artifacts"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

metadata = get_home_dropdwon_info()
# dataset  = load_dataset()
with open(r"artifacts\model\random_forest_model.pkl", "rb") as f:
    loaded_model = pickle.load(f)

@app.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        global log_file
        form = await request.form
        username = form.get("username")
        password = form.get("password")
        
        session["username"] = username
        log_file = create_log_files(user_name=username)

        if USERS.get(username) == password:
            session["username"] = username

            log_file.info(f"User:{username} want to login")
            log_file.info("Login successful!")

            print(f"User:{username} want to login")

            await flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            await flash("Invalid credentials, please try again.", "danger")
    return await render_template("login.html")


@app.route("/logout")
async def logout():
    session.pop("username", None)
    session.pop("home_form_data", None)
    log_file.info("Logout successful!")
    print("Logout successful!")
    session.pop("page_form_data", None)
    await flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/")
async def home():
    if "username" in session:
        if metadata['dataset'].shape[0]!=0: 

            if metadata['selected_priority']!='All':   
                outcome = get_aggregated_info(metadata)

            if metadata['selected_priority']=='All':
                outcome = get_aggregated_info_all(metadata)
                metadata['selected_planner'] = 'All'
            
            # Statistical Information
            metadata['number_of_records']   = outcome["balance_exception_flag"]['Freq'].sum()
            header_raw_form                 = outcome["balance_exception_flag"]
            high_priority                   = header_raw_form[header_raw_form['Item Exception Flag']=='Above Max > $50 K (Red)']['Freq'].values[0]
            high_priority_status            = 'Above Max > $50 K (Red)'
            header_exception                = outcome["balance_exception"]
            metadata['number_of_exception'] = header_exception[header_exception['Exception Upg']=='cancelled']['Freq'].values[0]
            
            # print("metadata['number_of_exception']",metadata['number_of_exception'])
            if high_priority==0:
                high_priority = header_raw_form[header_raw_form['Item Exception Flag']=='Below Zero (Red)']['Freq'].values
                high_priority_status = 'Below Zero (Red)'
           
            metadata['high_priority_info'] = {'high_priority':str(high_priority).replace('[','').replace("]",''),
                                              'high_priority_info':high_priority_status}
            

            # print("Selected AI Priorit:",metadata['selected_priority'])
            filter_information =  metadata['dataset']

            if metadata['selected_priority']!='All':
               metadata['records'] = filter_information[filter_information['Planner Name Desc']==metadata['selected_planner']].values.tolist()

            if metadata['selected_priority']=='All':
               metadata['records'] = filter_information.values.tolist()

        if metadata['dataset'].shape[0]==0:
           outcome = {"balance_exception_flag":pd.DataFrame(),
                      "balance_exception":pd.DataFrame()}
           metadata['columns_info'] = []
           metadata['records']      = []
           metadata['number_of_records']   = 0
           metadata['number_of_exception'] = 0

           metadata['high_priority_info'] = {'high_priority':'0',
                                            'high_priority_info':''}
                      
        metadata['balance_exception_flag']   = outcome.get("balance_exception_flag")
        metadata['balance_exception']        = outcome.get("balance_exception")

        log_file.info('')
        log_file.info(f'User Selected:Planner Details:{metadata['selected_planner']}')
        log_file.info(f'User Selected: Assigned Priority:{metadata['selected_priority']}')
        log_file.info("----------------------------------------------------------------------")

        return await render_template(
            "home.html",
            username=session["username"],
            form_data=metadata,
            current_date=current_date,
            years = current_date.split("-")[0]
        )
    return redirect(url_for("login"))


@app.route("/submit_home_form", methods=["POST"])
async def submit_home_form():
    global metadata
    form                 = await request.form
    planner_name_desc_id = form.get("planner_name_desc_id")
    priority_selected    = form.get("assigned_priority")
    
    list_of_planner      = metadata['planner_name_desc']
    list_of_priority     = metadata['assigned_priority']

    updated_planner_info  = [planner_name_desc_id] + [row for row in  list_of_planner if row !=planner_name_desc_id]
    updated_priority_info = [priority_selected]   + [row for row in  list_of_priority if row !=priority_selected]
    
    metadata['planner_name_desc'] = updated_planner_info
    metadata['selected_planner']  = planner_name_desc_id
    metadata['assigned_priority'] = updated_priority_info
    metadata['selected_priority'] = priority_selected

    flash("Form submitted successfully for Home page!", "success")
    return redirect(url_for("home"))

@app.route('/upload',methods=["POST"])
async def upload():
    form = await request.files  # 👈 await here
    file = form.get("file")

    if  (file.filename != ""):
        filepath = f"artifacts/{file.filename}"
        await file.save(filepath) 
        metadata['filename'] = file.filename
        print(f"✅ File '{file.filename}' uploaded successfully at {filepath}")
        
        if file.filename.endswith(".csv"):
            df = pd.read_csv(filepath)

        if file.filename.endswith(".xlsx"):
            df = pd.read_excel(filepath)

        column_info = [cols for cols in mandatory_fields if cols in df.columns]
        
        if len(column_info)==len(mandatory_fields):
            print("Correct File is Uploaded")
            log_file.info("Correct File is Uploaded")
            target_cols = ['AI_PRIORITY'] 
            
            metadata['planner_name_desc'] = [row for row in df['Planner Name Desc'].unique()]
            metadata['exception']         = [row for row in df['Exception'].unique() if row not in exception] + exception
            metadata['item_exception_flag'] = [row for row in df['Item Exception Flag'].unique() if row not in item_exception_flag] + item_exception_flag
            
            # selected_cols = target_cols +[cols for cols in df.columns if cols not in target_cols]
            # metadata['dataset']             = df[selected_cols]
            metadata['selected_planner']    = metadata['planner_name_desc'][0]
            # metadata['number_of_records']   = df.shape[0]

            # metadata['number_of_records']   = metadata['dataset'].shape[0]
            predicted_records = predictions(df,feature_mapping,loaded_model)
            predicted_records.drop(columns=['Id'],inplace=True)
            metadata['dataset']             = predicted_records  #df[selected_cols]
            metadata['columns_info']        = [row for row in metadata['dataset'].columns]#[:3]
            metadata['records']             = metadata['dataset'].values.tolist()

            # print(predicted_records)
        
        if len(column_info)!=len(mandatory_fields):
            print("Wrong File is Uploaded")
            log_file.info("Wrong File is Uploaded")
            metadata['planner_name_desc'] = ['Not Found']
            metadata['exception']         = ['Not Found']
            metadata['item_exception_flag'] = ['Not Found']
            metadata['selected_planner']    = 'Not Found'
            metadata['dataset']             = pd.DataFrame()
            metadata['number_of_records']   = 0

    if file.filename == "":
        
        source_file_path = os.path.join(app.config["UPLOAD_FOLDER"], metadata['filename'])
        print("Deleted ",source_file_path)

        log_file.info(f"Deleted File from source:{source_file_path}")
        if os.path.exists(source_file_path):
           os.remove(source_file_path)

        metadata['filename'] = 'No file selected for AI/ML prediction'
        metadata['planner_name_desc'] = ['Not Found']
        metadata['exception']         = ['Not Found'] 
        metadata['item_exception_flag'] = ['Not Found'] 
        metadata['dataset']           = pd.DataFrame()
        metadata['selected_planner']    = 'Not Found'

        metadata['columns_info'] = []
        metadata['records']      = []
        metadata['number_of_records']   = 0

    flash("Form submitted successfully for Home page!", "success")
    return redirect(url_for("home"))

@app.route("/bar-exception-chart")
async def bar_exception_chart():
    # print( metadata['strategy_past_history'])
    plotdata = await asyncio.to_thread(bar_plot, 
                                       information = metadata['balance_exception'],
                                       type_plot   = 'Exception')
    # Convert the chart to JSON
    graph_json = pio.to_json(plotdata)
    return jsonify({"graph_json": graph_json})  

@app.route("/bar-exception-flag-chart")
async def bar_exception_flag_data():
    # print( metadata['strategy_past_history']type_plot =='Exception')
    plotdata = await asyncio.to_thread(bar_plot, 
                                       information  = metadata['balance_exception_flag'],
                                       type_plot    = 'Item Exception Flag')
    # Convert the chart to JSON
    graph_json = pio.to_json(plotdata)
    return jsonify({"graph_json": graph_json}) 


@app.route("/download_excel")
async def download_excel():
    
    if metadata['dataset'].shape[0]!=0:
        filter_information =  metadata['dataset']
        
        if metadata['selected_priority']!='All':
            download_data = filter_information[filter_information['Planner Name Desc']==metadata['selected_planner']]

        if metadata['selected_priority']=='All':
            download_data = filter_information

    if metadata['dataset'].shape[0]==0:
        download_data = pd.DataFrame()

    # Write Excel to in-memory buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        download_data.to_excel(writer, index=False, sheet_name="Sheet1")
    output.seek(0)

    return await send_file(
        output,
        as_attachment=True,
        attachment_filename="recommendations.xlsx",  # ✅ use this in Quart
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host="0.0.0.0", port=5010)