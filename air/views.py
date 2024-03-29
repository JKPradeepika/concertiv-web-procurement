from django.shortcuts import render
from django.views.generic import View
from django.core.exceptions import ValidationError

from .forms import AirRawdataForm
from .models import Airline, Airport, Alliance, FactTable

from CPR.settings.dev import OSC_CLIENT_ID, OSC_CLIENT_SECRET
from CPR.settings.base import BASE_DIR

from pathlib import Path, PureWindowsPath
import os
import json
import pandas as pd
import datetime
import jwt
import csv
import errno
import shutil
from decouple import config
from sqlalchemy import create_engine
import psycopg2
import psycopg2.extras as extras

# Create your views here.
class BasicView(View):

    # Function to return config file path
    def config_path(self):
        cwd = os.getcwd()
        config_json_file_path = Path(os.path.join(cwd, "config.json"))
        with open(config_json_file_path) as f:
            data = json.load(f)
        return data

    # Function to return path of windows path of raw data file
    def base_path(self):
        data = self.config_path()
        username = os.getlogin()
        user_path = Path(os.path.join("C:/Users", username))
        elt_file_path = data["win_etl_output_files_path"]
        win_etl_file_path = Path(os.path.join(user_path, elt_file_path))
        return win_etl_file_path
    
    # Function to return path for oneschema - air
    def oneschema_air_path(self):
        username = os.getlogin()
        user_path = Path(os.path.join("C:/Users", username))
        data = self.config_path()
        oneschema_air_path = Path(os.path.join(user_path, data["oneschema_air_path"]))
        return oneschema_air_path

    # Function which returns Year Half based on Quarter
    def half_year(self, quarter):
        if quarter == "Q1" or quarter == "Q2":
            return "H1"
        else:
            return "H2"

    # Function which returns contract classifier for all Prism flights
    def savings_classifier(self, classifier_names, jet_departure_date, jet_booking_class_code, emi_references, tur_references, qan_references, sin_references):
        jet_ctv_references, emi_ctv_references, tur_ctv_references, qan_ctv_references, sin_ctv_references, jet_indexes, emi_indexes, tur_indexes, qan_indexes, sin_indexes = [], [], [], [], [], [], [], [], [], []
        data = self.config_path()
        for cn in range(len(classifier_names)):
            if classifier_names[cn] == "JetBlue":
                jet_indexes.append(cn)
            elif classifier_names[cn] == "Emirates":
                emi_indexes.append(cn)
            elif classifier_names[cn] == "Turkish":
                tur_indexes.append(cn)
            elif classifier_names[cn] == "Qantas":
                qan_indexes.append(cn)
            elif classifier_names[cn] == "Singapore":
                sin_indexes.append(cn)
        for jd in range(len(jet_departure_date)):
            dd = data["jet_departure_date"]
            [jet_ctv_references.append(''.join("Pre May 2019" + "-" + bc)) if jet_departure_date[jd] <= dd else jet_ctv_references.append(''.join("Post May 2019" + "-" + bc)) for bc in jet_booking_class_code[jd]]
        [emi_ctv_references.append(e) for e in emi_references]
        [tur_ctv_references.append(t) for t in tur_references]
        [qan_ctv_references.append(q) for q in qan_references]
        [sin_ctv_references.append(s) for s in sin_references]
        return jet_ctv_references, emi_ctv_references, tur_ctv_references, qan_ctv_references, sin_ctv_references, jet_indexes, emi_indexes, tur_indexes, qan_indexes, sin_indexes

    # Function to return tour code and ticket designator for all Prism airlines based on savings contract classifier
    def tour_code_and_ticket_designator(self):
        jet_tour_code, jet_ticket_designator, emi_tour_code, emi_ticket_designator, tur_tour_code, tur_ticket_designator, qan_tour_code, sin_tour_code, sin_ticket_designator = "", "", "", "", "", "", "", "", ""
        data = self.config_path()
        for k, v in data["tour_code_and_ticket_designator"].items():
            if k == "JetBlue":
                for k1, v1 in v.items():
                    jet_tour_code = v["jet_tour_code"]
                    jet_ticket_designator = v["jet_ticket_designator"]
            elif k == "Emirates":
                for k1, v1 in v.items():
                    emi_tour_code = v["emi_tour_code"]
                    emi_ticket_designator = v["emi_ticket_designator"]
            elif k == "Turkish":
                for k1, v1 in v.items():
                    tur_tour_code = v["tur_tour_code"]
                    tur_ticket_designator = v["tur_ticket_designator"]
            elif k == "Qantas":
                for k1, v1 in v.items():
                    qan_tour_code = v["qan_tour_code"]
            elif k == "Singapore":
                for k1, v1 in v.items():
                    sin_tour_code = v["sin_tour_code"]
                    sin_ticket_designator = v["sin_ticket_designator"]
        return jet_tour_code, jet_ticket_designator, emi_tour_code, emi_ticket_designator, tur_tour_code, tur_ticket_designator, qan_tour_code, sin_tour_code, sin_ticket_designator

    # Function to read Group Mappings for Preferred Savings Classifiers
    def read_group_mappings(self):
        username = os.getlogin()
        user_path = Path(os.path.join("C:/Users", username))
        data = self.config_path()
        group_mapping_file_path = data["air_group_mapping_path"]
        group_mapping_file = Path(os.path.join(user_path, group_mapping_file_path))
        path = PureWindowsPath(group_mapping_file)
        full_file_path = Path(os.path.join(path, "Group Airline Discounts Mapping.xlsx"))
        csv_file_path = Path(os.path.join(path, "Group Airline Discounts Mapping.csv"))
        xl = pd.ExcelFile(full_file_path)
        df = pd.read_excel(xl, sheet_name=None)
        df = pd.concat(df, ignore_index=True)
        df.to_csv(csv_file_path, encoding='utf-8', index=False)
        df = pd.read_csv(csv_file_path)
        return df

    # Function to assign discount based on reference_list
    def assign_discount(self, discount, discount_reference_list, indices_list, reference_list, df):
        loc_list = []
        for tk in discount_reference_list:
            if tk in reference_list:
                index = int(df[df["Reference"] == tk].index[0])
                loc = df.at[index, "Discount"]
                loc_list.append(loc)
            else:
                missing_value = 99999.9
                loc_list.append(missing_value)
        p = dict(zip(indices_list, loc_list))
        m = list(p.values())
        j = list(p.keys())
        for i in range(len(discount)):
            for k in range(len(j)):
                if i == j[k]:
                    discount[i] = m[k]
        return discount

    # Function to check whether the tour code and ticket designator are available or not to determine discount
    def check_tour_code_and_ticket_designator(self, df, discount, savings_tour_code, savings_ticket_designator, index_list, tour_code, ticket_designator):
        group = self.read_group_mappings()
        reference_list = group["Reference"].tolist()
        discount_contract_classifier = df["Savings Contract Classifier"].tolist()
        discount_reference_list, indices_list = [], []
        for i in range(len(index_list)):
            df_tour_code = str(df["Tour Code"].iloc[index_list[i]])
            df_ticket_designator = str(df["Ticket Designator"].iloc[index_list[i]])
            if (df_tour_code == "" or df_tour_code == "nan") and (df_ticket_designator == "" or df_ticket_designator == "nan"):
                savings_tour_code[index_list[i]] = "Not Available, Not Matched"
                savings_ticket_designator[index_list[i]] = "Not Available, Not Matched"
            elif (df_tour_code != "" and df_tour_code != "nan" and df_tour_code == tour_code) and (df_ticket_designator != "" and df_ticket_designator != "nan" and df_ticket_designator == ticket_designator):
                savings_tour_code[index_list[i]] = "Available, Matched"
                savings_ticket_designator[index_list[i]] = "Available, Matched"
                discount_reference_list.append(discount_contract_classifier[index_list[i]])
                indices_list.append(index_list[i])
                self.assign_discount(discount, discount_reference_list, indices_list, reference_list, group)
            elif (df_tour_code != "" and df_tour_code != "nan" and df_tour_code != tour_code) and (df_ticket_designator != "" and df_ticket_designator != "nan" and df_ticket_designator != ticket_designator):
                savings_tour_code[index_list[i]] = "Available, Not Matched - " + df_tour_code
                savings_ticket_designator[index_list[i]] = "Available, Not Matched - " + df_ticket_designator
            elif (df_tour_code != "" or df_tour_code != "nan")  and (df_ticket_designator == "" or df_ticket_designator == "nan"):
                savings_ticket_designator[index_list[i]] = "Not Available, Not Matched"
                if df_tour_code != tour_code:
                    savings_tour_code[index_list[i]] = "Available, Not Matched - " + df_tour_code
                else:
                    savings_tour_code[index_list[i]] = "Available, Matched"
                    discount_reference_list.append(discount_contract_classifier[index_list[i]])
                    indices_list.append(index_list[i])
                    self.assign_discount(discount, discount_reference_list, indices_list, reference_list, group)
            elif (df_tour_code == "" or df_tour_code == "nan") and (df_ticket_designator != "" or df_ticket_designator != "nan"):
                savings_tour_code[index_list[i]] = "Not Available, Not Matched"
                if df_ticket_designator != ticket_designator:
                    savings_ticket_designator[index_list[i]] = "Available, Not Matched - " + df_ticket_designator
                else:
                    savings_ticket_designator[index_list[i]] = "Available, Matched"
                    discount_reference_list.append(discount_contract_classifier[index_list[i]])
                    indices_list.append(index_list[i])
                    self.assign_discount(discount, discount_reference_list, indices_list, reference_list, group)
            elif (df_tour_code != "" and df_tour_code != "nan" and df_tour_code == tour_code) and (df_ticket_designator != "" and df_ticket_designator != "nan" and df_ticket_designator != ticket_designator):
                savings_tour_code[index_list[i]] = "Available, Matched"
                savings_ticket_designator[index_list[i]] = "Available, Not Matched - " + df_ticket_designator
                discount_reference_list.append(discount_contract_classifier[index_list[i]])
                indices_list.append(index_list[i])
                self.assign_discount(discount, discount_reference_list, indices_list, reference_list, group)
            elif (df_tour_code != "" and df_tour_code != "nan" and df_tour_code != tour_code) and (df_ticket_designator != "" and df_ticket_designator != "nan" and df_ticket_designator == ticket_designator):
                savings_tour_code[index_list[i]] = "Available, Not Matched - " + df_tour_code
                savings_ticket_designator[index_list[i]] = "Available, Matched"
                discount_reference_list.append(discount_contract_classifier[index_list[i]])
                indices_list.append(index_list[i])
                self.assign_discount(discount, discount_reference_list, indices_list, reference_list, group)
        return discount, savings_tour_code, savings_ticket_designator

    # Function returns discount, pre-discount and savings for Prism flights
    def prism_flights_info(self, file_path, csv_file_path, quarter_year, prism_airlines):
        prism_discount_list = []
        xl = pd.ExcelFile(file_path)
        df = pd.read_excel(xl, sheet_name="Air - PRISM & Other")
        df.to_csv(csv_file_path, encoding='utf-8', index=False)
        df = pd.read_csv(csv_file_path)
        index_list = df.index[df["Quarter"] == quarter_year].tolist()
        for i, p in zip(index_list, prism_airlines):
            prism_discount_list.append(p)
            pre_discount = df.iloc[[i, "Pre-Discount"]]
            pre_discount = "{:,.2f}".format(pre_discount)
            prism_discount_list.append(pre_discount)
            actual_spend = df.iloc[[i,"Actual Spend"]]
            actual_spend = "{:,.2f}".format(actual_spend)
            prism_discount_list.append(actual_spend)
            savings = df.iloc[[i,"Savings"]]
            savings = "{:,.2f}".format(savings)
            prism_discount_list.append(savings)
        return prism_discount_list

    # Function to calculate the total Pre discount, Savings and Fare
    def calculate_total(self, df, airline_list, airline_indexes, airline_pre_discount, airline_fare, airline_savings, total_prism_pre_discount, total_prism_actual_spend, total_prism_vol, total_prism_savings, total_prism_net):
        total_non_prism_pre_discount, total_non_prism_actual_spend, total_non_prism_vol, total_non_prism_savings, total_non_prism_net, total_non_prism_final_savings = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        total_non_prism_pre_discount = total_prism_pre_discount + airline_pre_discount
        pre_discount = "$" + "{:,.2f}".format(airline_pre_discount)
        airline_list.append(pre_discount)
        total_non_prism_actual_spend = total_prism_actual_spend + airline_fare
        fare = "$" + "{:,.2f}".format(airline_fare)
        airline_list.append(fare)
        vol = len(airline_indexes) / len(df.index)
        vol = (vol * 100)
        total_non_prism_vol = total_prism_vol + vol
        vol = "{:,.2f}".format(vol) + "%"
        airline_list.append(vol)
        total_non_prism_savings = total_prism_savings + airline_savings
        savings = "$" + "{:,.2f}".format(airline_savings)
        airline_list.append(savings)
        net = (airline_savings / airline_pre_discount) * 100
        total_non_prism_net = total_prism_net + net
        net = "{:,.2f}".format(net) + "%"
        airline_list.append(net)
        sum_savings = df["Savings"].sum()
        total_non_prism_final_savings = total_prism_savings + sum_savings * 2
        savings = "$" + "{:,.2f}".format(sum_savings)
        airline_list.append(savings)
        return airline_list, total_non_prism_pre_discount, total_non_prism_actual_spend, total_non_prism_vol, total_non_prism_savings, total_non_prism_net, total_non_prism_final_savings

        
class RawDataView(BasicView):
    form_class = AirRawdataForm
    template_name = 'air/raw_data.html'
    success_url = 'air/get_raw_data.html'
    error_url = 'commons/error.html'
    
    # Function to get the raw data - air
    def get(self, request, *args, **kwargs):
        if request.session.has_key('username'):
            username = request.session.get('username')
            request.session.modified = True
            form = self.form_class
            return render(request, self.template_name, context={'form': form, 'username': username})
        else:
            message = "Unauthorized access. Please login again."
            return render(request, self.error_url, context={'message': message})
        
    # Function to post the raw data before oneschema
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        domain = "travel"
        travel_type = "Air"
        if request.session.has_key('username'):
            username = request.session.get('username')
            request.session.modified = True
            try:
                if form.is_valid():
                    customer_name = request.POST.get('customer_name')
                    travel_agency = request.POST.get('travel_agency')
                    quarter = request.POST.get('quarter')
                    year = request.POST.get('year')
                    country = request.POST.get('country')
                    data = {
                        'iss': OSC_CLIENT_ID,
                        'exp': datetime.datetime.now() + datetime.timedelta(minutes=15),
                        'user_id': username,
                        'customer_name': customer_name, 
                        'quarter': quarter, 
                        'year': year,
                        'travel_agency': travel_agency,
                        'country': country,
                        'domain': domain,
                        'travel_type': travel_type
                    }
                    encode_jwt = jwt.encode(payload = data, key=OSC_CLIENT_SECRET, algorithm='HS256')
                    context = {'username': username, 'customer_name': customer_name, 'quarter': quarter, 'year': year, 'country': country, 'travel_agency': travel_agency, 'encode_jwt': encode_jwt, 'domain': domain, 'travel_type': travel_type}
                    return render(request, self.success_url, context)
                else:
                    form = self.form_class(request.POST)
            except IOError as e:
                if e.errno == errno.EPIPE:
                    pass
        else:
            message = "Unauthorized access. Please login again."
            return render(request, self.error_url, context={'message': message})
        return render(request, self.template_name, context={'form': form, 'username': username})

class LoadRawDataView(BasicView):
    template_name = 'air/load_raw_data.html'
    error_url = 'commons/error.html'
        
    def post(self, request, *args, **kwargs):
        if request.session.has_key('username'):
            username = request.session.get('username')
            request.session.modified = True
            osc_jwt_token = request.headers['Authorization']
            decode_jwt = jwt.decode(osc_jwt_token, OSC_CLIENT_SECRET, algorithms=["HS256"])
            if decode_jwt.get('iss') == OSC_CLIENT_ID:
                customer_name = decode_jwt.get('customer_name')
                quarter = decode_jwt.get('quarter')
                year = decode_jwt.get('year')
                country = decode_jwt.get('country')
                travel_agency = decode_jwt.get('travel_agency')
                travel_type = decode_jwt.get('travel_type')
                payload = json.loads(request.body.decode('utf-8'))
                column_headers, template_key_headers = [], []
                for col in payload.get('columns'):
                    for k, v in col.items():
                        if k == "template_column_name":
                            column_headers.append(v)
                        elif k == "template_column_key":
                            template_key_headers.append(v)
                final_rec, rows = [], [] 
                for rec in payload.get('records'):
                    reordered_dict = {k: rec[k] for k in template_key_headers}
                    rows = list(reordered_dict.values())
                    final_rec.append(rows)
                one_schema_air_path = self.oneschema_air_path()
                final_oneschema_payload_path = PureWindowsPath(one_schema_air_path)
                csv_file_name = "{}_{}_{}{}_{}.csv".format(customer_name, travel_type, quarter, year, country)
                csv_file_path = Path(os.path.join(final_oneschema_payload_path, csv_file_name))
                with open(csv_file_path, 'w', newline='') as csv_file:
                    csv_writer = csv.writer(csv_file)
                    csv_writer.writerow(column_headers)
                    csv_writer.writerows(final_rec)
                context = {'username': username, 'customer_name': customer_name, 'quarter': quarter, 'year': year, 'country': country, 'travel_agency': travel_agency, 'travel_type': travel_type, 'csv_file_path': csv_file_path}
                return render(request, self.template_name, context)   
        else:
            message = "Unauthorized access. Please login again."
            return render(request, self.error_url, context={'message': message})
        return render(request, self.template_name, {'username': username})


class ProcessDataView(BasicView):
    template_name = 'air/final_rec.html'
    error_url = 'commons/error.html'

    def post(self, request, *args, **kwargs):
        # Reading CSV file
        if request.session.has_key('username'):
            username = request.session.get('username')
            request.session.modified = True
            src_csv_file_path = request.POST.get('csv_file_path')
            final_dropbox_path, group_mapping_file_path = "", ""
            customer_name = request.POST.get('customer_name')
            travel_agency = request.POST.get('travel_agency')
            travel_type = request.POST.get('travel_type')
            country = request.POST.get('country')
            year = request.POST.get('year')
            quarter = request.POST.get('quarter')
            conn = psycopg2.connect(database=config('DEV_DB_NAME'), user=config('DEV_DB_USER'),password=config('DEV_DB_PASSWORD'), host=config('DB_HOST'),port=config('DB_PORT'))   
            try:
                if os.path.exists(src_csv_file_path):
                    win_etl_file_path = self.base_path()
                    win_etl_output_file_path = Path(os.path.join(win_etl_file_path, customer_name))
                    dropbox_path = Path(os.path.join(win_etl_output_file_path, "3. Performance Reports", year, quarter, "Raw TMC Data-Dev"))
                    final_dropbox_path = PureWindowsPath(dropbox_path)
                    csv_file_name = "{}_{}_{}{}_{}.csv".format(customer_name, travel_type, quarter, year, country)
                    dest_csv_file_path = Path(os.path.join(final_dropbox_path, csv_file_name))
                    shutil.copy(src_csv_file_path, dest_csv_file_path)
                    df = pd.read_csv(dest_csv_file_path)
                    
                    # Group mappings file path
                    user = os.getlogin()
                    user_path = Path(os.path.join("C:/Users", user))
                    data = self.config_path()
                    group_mapping_file_path = data["air_group_mapping_path"]
                    group_mapping_file = Path(os.path.join(user_path, group_mapping_file_path))
                    group_mapping_file_path = PureWindowsPath(group_mapping_file)

                    # Get data from database tables
                    alliance_qs = Alliance.objects.all()
                    alliance_data = list(alliance_qs.values())
                    
                    airport_qs = Airport.objects.all()
                    airport_data = list(airport_qs.values())

                    airline_qs = Airline.objects.all()
                    airline_data = list(airline_qs.values())
                    
                    # Converting airport and carrier codes in dataframe to list
                    airport_ori_code = df["Origin Airport Code"].tolist()
                    airport_dest_code = df["Destination Airport Code"].tolist()
                    carrier_code = df["Carrier Code"].tolist()
                    
                    # Setting rows display
                    pd.set_option('display.max_rows', 1500)
                    
                    # Check if columns exists in dataframe
                    if "Tax" in df.columns:
                        df["Tax"] = df["Tax"].tolist()
                    else:
                        df["Tax"] = ""
                        
                    if "Invoice Number" in df.columns:
                         df["Invoice Number"] = df["Invoice Number"].tolist()
                    else:
                        df["Invoice Number"] = ""
                    
                    if "Booked Date / Invoice Date" in df.columns:
                        df["Booked Date / Invoice Date"] = pd.to_datetime(df["Booked Date / Invoice Date"]).dt.strftime("%m/%d/%Y")
                    else:
                        df["Booked Date / Invoice Date"] = ""
                        
                    if "Tour Code" in df.columns:
                        tour_code = df["Tour Code"].tolist()
                        df["Tour Code"] = [tc for tc in tour_code]
                    else:
                        df["Tour Code"] = ""
                    
                    if "Ticket Designator" in df.columns:
                        ticket_designator = df["Ticket Designator"].tolist()
                        df["Ticket Designator"] = [td for td in ticket_designator]
                    else:
                        df["Ticket Designator"] = ""
                    
                    # Forming dataframe for final data
                    df['Departure Date'] = pd.to_datetime(df['Departure Date'], format="%m/%d/%Y")
                    df.insert(0, "Travel Date Quarter", 'Q' + df['Departure Date'].dt.quarter.astype(str) + " " + df['Departure Date'].dt.year.astype(str), True)
                    df.insert(1, "Travel Date Half Year", 'H' + df['Departure Date'].dt.month.gt(6).add(1).astype(str) + " " + df['Departure Date'].dt.year.astype(str), True)
                    df.insert(2, "Travel Date Year", year, True)
                    df.insert(3, "Client", customer_name, True)
                    df.insert(4, "Agency", travel_agency, True)
                    df.insert(5, "PoS", country, True)
                    traveller_names = df['Traveller Name'].tolist()
                    df["Traveller Name"] = [i.replace('/', ', ') for i in traveller_names]
                    df["Carrier Name"] = [i["carrier_name"] for cc in carrier_code for i in airline_data for k, v in i.items() if cc == v]
                    df["PNR Locator"] = df["PNR"]
                    df["Miles / Mileage"] = df["Segment Miles"]
                    df["CTV_Booking Class Code"] = df["Class of Service Code"]
                    df["CTV_Origin_Airport_Id"] = [i["airport_id"] for oc in airport_ori_code for i in airport_data for k, v in i.items() if oc == v]
                    df["CTV_Destination_Airport_Id"] = [i["airport_id"] for dc in airport_dest_code for i in airport_data for k, v in i.items() if dc == v]
                    df["CTV_Reference"] = df["Origin Airport Code"] + "-" + df["Destination Airport Code"] + "-" + df["Class of Service Code"]
                    df["CTV_Fare"] = df["Class of Service"]
                    df["CTV_Carrier_Id"] = [i["carrier_id"] for cc in carrier_code for i in airline_data for k, v in i.items() if cc == v]
                    df["CTV_Alliance_ID"] = [i["carrier_alliance_id"] for cc in carrier_code for i in airline_data for k, v in i.items() if cc == v]
                    alliance_data_list = df["CTV_Alliance_ID"].tolist()
                    df["Savings Alliance Classification"] = [i["alliance_name"] for adl in alliance_data_list for i in alliance_data for k, v in i.items() if adl == v]

                    # Determine savings classifier based on departure data for Prism airlines
                    savings_alliance_classifier = df["Savings Alliance Classification"].tolist()
                    jet_departure_date_df = df.loc[df["Savings Alliance Classification"] == "JetBlue", "Departure Date"]
                    jet_departure_date_df = jet_departure_date_df.map(str)
                    jet_departure_date = jet_departure_date_df.tolist()
                    jet_booking_class_code_df = df.loc[df["Savings Alliance Classification"] == "JetBlue", "CTV_Booking Class Code"]
                    jet_booking_class_code_df = jet_booking_class_code_df.map(str)
                    jet_booking_class_code = jet_booking_class_code_df.tolist()
                    emi_references_df = df.loc[df["Savings Alliance Classification"] == "Emirates", "CTV_Reference"]
                    emi_references_df = emi_references_df.map(str)
                    emi_references = emi_references_df.tolist()
                    tur_references_df = df.loc[df["Savings Alliance Classification"] == "Turkish", "CTV_Reference"]
                    tur_references_df = tur_references_df.map(str)
                    tur_references = tur_references_df.tolist()
                    qan_references_df = df.loc[df["Savings Alliance Classification"] == "Qantas", "CTV_Reference"]
                    qan_references_df = qan_references_df.map(str)
                    qan_references = qan_references_df.tolist()
                    sin_references_df = df.loc[df["Savings Alliance Classification"] == "Singapore", "CTV_Reference"]
                    sin_references_df = sin_references_df.map(str)
                    sin_references = sin_references_df.tolist()

                    jet_ctv_references, emi_ctv_references, tur_ctv_references, qan_ctv_references, sin_ctv_references, jet_indexes, emi_indexes, tur_indexes, qan_indexes, sin_indexes = self.savings_classifier(savings_alliance_classifier, jet_departure_date, jet_booking_class_code, emi_references, tur_references, qan_references, sin_references)
                    jet_tour_code, jet_ticket_designator, emi_tour_code, emi_ticket_designator, tur_tour_code, tur_ticket_designator, qan_tour_code, sin_tour_code, sin_ticket_designator = self.tour_code_and_ticket_designator()
                    df["Departure Date"] = pd.to_datetime(df["Departure Date"]).dt.strftime("%m/%d/%Y")
                    contract_classifier  = []
                    [contract_classifier.append("Not Preferred Airlines") for i in range(len(savings_alliance_classifier))]
                    for i in savings_alliance_classifier:
                        if i == "JetBlue":
                            for j in range(len(jet_indexes)):
                                contract_classifier[jet_indexes[j]] = jet_ctv_references[j]
                        if i == "Emirates":
                            for e in range(len(emi_indexes)):
                                contract_classifier[emi_indexes[e]] = emi_ctv_references[e]
                        elif i == "Turkish":
                            for t in range(len(tur_indexes)):
                                contract_classifier[tur_indexes[t]] = tur_ctv_references[t]
                        elif i == "Qantas":
                            for q in range(len(qan_indexes)):
                                contract_classifier[qan_indexes[q]] = qan_ctv_references[q]
                        elif i == "Singapore":
                            for s in range(len(sin_indexes)):
                                contract_classifier[sin_indexes[s]] = sin_ctv_references[s]

                    
                    df["Savings Contract Classifier"] = [j for j in contract_classifier]
                    
                    # Validating tour code and ticket designator
                    savings_tour_code, savings_ticket_designator, discount = [], [], []
                    for i in range(len(savings_alliance_classifier)):
                        savings_tour_code.append("Not Preferred Airlines")
                        savings_ticket_designator.append("Not Preferred Airlines")
                    
                    default_discount = 0.00
                    [discount.append(default_discount) for i in range(len(savings_alliance_classifier))]

                    # Checking tour code and ticket designator for Non Prism Flights
                    for i in range(len(savings_alliance_classifier)):
                        if savings_alliance_classifier[i] == "JetBlue":
                            discount, savings_tour_code, savings_ticket_designator = self.check_tour_code_and_ticket_designator(df, discount, savings_tour_code, savings_ticket_designator, jet_indexes, jet_tour_code, jet_ticket_designator)
                        elif savings_alliance_classifier[i] == "Emirates":
                            discount, savings_tour_code, savings_ticket_designator = self.check_tour_code_and_ticket_designator(df, discount, savings_tour_code, savings_ticket_designator, emi_indexes, emi_tour_code, emi_ticket_designator)
                        elif savings_alliance_classifier[i] == "Turkish":
                            discount, savings_tour_code, savings_ticket_designator = self.check_tour_code_and_ticket_designator(df, discount, savings_tour_code, savings_ticket_designator, tur_indexes, tur_tour_code, tur_ticket_designator)
                        elif savings_alliance_classifier[i] == "Qantas":
                            discount, savings_tour_code, savings_ticket_designator = self.check_tour_code_and_ticket_designator(df, discount, savings_tour_code, savings_ticket_designator, qan_indexes, qan_tour_code, "nan")
                        elif savings_alliance_classifier[i] == "Singapore":
                                discount, savings_tour_code, savings_ticket_designator = self.check_tour_code_and_ticket_designator(df, discount, savings_tour_code, savings_ticket_designator, sin_indexes, sin_tour_code, sin_ticket_designator)
                    
                    df["Contract Classifier Tour Code"] = [tc for tc in savings_tour_code]
                    df["Contract Classifier Ticket Designator"] = [td for td in savings_ticket_designator]
                    discount_if_applied = []
                    classifier_tour_code = df["Contract Classifier Tour Code"].tolist()
                    classifier_ticket_designator = df["Contract Classifier Ticket Designator"].tolist()
                    [discount_if_applied.append("Y") if ctc == "Available, Matched" or ctd == "Available, Matched" else discount_if_applied.append("N") for ctc, ctd in zip(classifier_tour_code, classifier_ticket_designator)]
                    df["If Discount Applied"] = [da for da in discount_if_applied]
                    df["Discount"] = [d for d in discount]
                    currency = list()
                    if 'Currency Code' not in df.columns:
                        for i in range(len(savings_tour_code)):
                            currency.append("USD")
                    df["Currency Code"] = [c for c in currency]
                    pre_dis, pre, sav = [], [], []
                    fare = df["Fare"].tolist()
                    discount = df["Discount"].tolist()
                    pre_dis, pre, sav, reference_code_missing, non_prism = [], [], [], [], []
                    [reference_code_missing.append("Y") if d == 99999.9 else reference_code_missing.append("N") for d in discount]
                    df["If Reference Missing"] = [ref for ref in reference_code_missing]
                    [pre.append(1 - d) for d in discount]
                    [pre_dis.append(f / d) for f, d in zip(fare, pre)]
                    df["Pre-Discount Cost"] = [pr for pr in pre_dis]
                    df["Pre-Discount Cost"] = df["Pre-Discount Cost"].round(2)
                    pre_disc_cost = df["Pre-Discount Cost"].tolist()
                    [sav.append(pre - f) for f, pre in zip(fare, pre_disc_cost)]
                    df["Savings"] = [s for s in sav]
                    df["Savings"] = df["Savings"].round(2)
                    data = self.config_path()
                    for ali in range(len(savings_alliance_classifier)):
                        non_prism.append("Y")
                        if savings_alliance_classifier[ali] in data["group_deals"]:
                            non_prism[ali] = "N"
                    df["Non-Prism Preferred"] = [np for np in non_prism]
                    
                    
                    
                    # Prism flights data still pending....
                    
                    # Rearranging the columns
                    headers = ["Travel Date Quarter", "Travel Date Half Year", "Travel Date Year", 
                            "Client", "Agency", "PoS", "Traveller Name", 
                            "Departure Date", "Booked Date / Invoice Date","Carrier Code", "Carrier Name", 
                            "Class of Service Code", "Origin Airport Code", "Destination Airport Code", 
                            "Tour Code", "Ticket Designator", "Fare", "Currency Code", "Tax", "Miles / Mileage", "Invoice Number",
                            "PNR Locator", "CTV_Booking Class Code", "CTV_Origin_Airport_Id", 
                            "CTV_Destination_Airport_Id", "CTV_Fare", "CTV_Reference", "CTV_Carrier_Id", "CTV_Alliance_ID", 
                            "Savings Alliance Classification", "Savings Contract Classifier", "Discount", "Pre-Discount Cost", 
                            "Savings", "Non-Prism Preferred", "Contract Classifier Tour Code", "Contract Classifier Ticket Designator", 
                            "If Discount Applied", "If Reference Missing"]

                    df = df.reindex(columns=headers)

                    # Writing new column names into separate .xlsx file
                    win_etl_file_path = self.base_path()
                    new_file_name = "{}_{}_{}{}_{}_FinalData.xlsx".format(customer_name, travel_type, quarter, year, country)
                    file_name = Path(os.path.join(final_dropbox_path, new_file_name))
                    df.to_excel(file_name, index=False)
                    
                    
                    # Saving data from .xlsx file to DB
                    db_df = pd.read_excel(file_name)
                    db_df = df[["Travel Date Quarter", "Client", "Traveller Name", "Booked Date / Invoice Date",
                           "Departure Date", "Carrier Code", "Class of Service Code", "Origin Airport Code",
                           "Destination Airport Code", "Tour Code", "Ticket Designator", "PoS", "Fare",
                           "Tax", "Miles / Mileage", "PNR Locator", "Discount", "Invoice Number", "Currency Code"]].copy()
                    db_df.rename(columns={"Travel Date Quarter": "data_receive_quarter", "Client": "client_name", "Traveller Name": "traveller_name",
                                          "Booked Date / Invoice Date": "booked_date_or_invoice_date", "Departure Date": "departure_date", "Carrier Code": "carrier_code_id", 
                                          "Class of Service Code": "class_of_service_code", "Origin Airport Code": "origin_airport_code_id", 
                                          "Destination Airport Code": "destination_airport_code_id", "Tour Code": "tour_code", "Ticket Designator": "ticket_designator", 
                                          "PoS": "point_of_sale", "Fare": "fare", "Tax": "tax", "Miles / Mileage": "miles_or_mileage", "PNR Locator": "pnr_locator", 
                                          "Discount": "discount", "Invoice Number": "invoice_number", "Currency Code": "currency_code"}, inplace=True)
                    db_excel_file_name = "{}_{}_{}{}_{}_DBFinalData.xlsx".format(customer_name, travel_type, quarter, year, country)
                    db_excel_file_path = Path(os.path.join(final_dropbox_path, db_excel_file_name))
                    db_df.to_excel(db_excel_file_path, index=False)
                    
                    # Saving final data into database
                    table = "air_facttable"
                    cols = ','.join((db_df.columns).to_list())                   
                    for x in db_df.to_numpy():
                        if x[16] == 99999.9:
                             raise ValidationError("Reference code is available but Discount is not applied. Please check")
                        else:
                            query = "INSERT INTO {0} ({1}) VALUES {2}".format(table, cols, tuple(x)) 
                            cursor = conn.cursor()
                            cursor.execute(query)
                            cursor.close()
                    conn.commit()
                    conn.close()
                    
                    context = {'username': username, 'customer_name': customer_name, 'quarter': quarter, 'year': year, 'country': country, 'final_sheet': file_name}
                    return render(request, self.template_name, context=context)
            except ValidationError as v:
                print(v.message)
                conn.rollback()
                context = {'message': v.message}
                return render(request, self.error_url, context)
            except psycopg2.DatabaseError as error:
                print("Error: %s" % error)
                conn.rollback()
                context = {'message': error}
                return render(request, self.error_url, context)
            except FileNotFoundError as error:
                message = ("Unable to find CSV file in specified directory: %s" % src_csv_file_path, error)
                context = {'message': message}
                return render(request, self.error_url, context)
            finally:
                # Deleting previous version of CSV - raw data file
                os.chdir(final_dropbox_path)
                pre_csv_file = "{}_{}_{}{}_{}.csv".format(customer_name, travel_type, quarter, year, country)
                if os.path.exists(pre_csv_file):
                    os.remove(pre_csv_file)

                # Deleting previous version of CSV - group mappings airline discounts file
                csv_file_path = Path(os.path.join(group_mapping_file_path, "Group Airline Discounts Mapping.csv"))
                if os.path.exists(csv_file_path):
                    os.remove(csv_file_path)

                # Moving back to project directory
                os.chdir(BASE_DIR)
        else:
            message = "Unauthorized access. Please login again."
            return render(request, self.error_url, context={'message': message})
        return render(request, self.template_name, context={'username': username})

