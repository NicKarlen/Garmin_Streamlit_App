import logging
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import timedelta, datetime, date
import numpy as np
import pandas as pd
import streamlit as st
import garmin_api as ga
#import openpyxl

ELEVATION_CORRECTION_UP = 4
ELEVATION_CORRECTION_DOWN = -2

# Start the logger
logging.basicConfig(filename='myapp.log',
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.info('Started')

st.set_page_config(layout="wide", initial_sidebar_state="expanded", page_title="Garmin Analytics", page_icon="https://cdn.iconscout.com/icon/free/png-256/free-garmin-3550671-2970276.png")

with st.sidebar:
    st.title("Garmin Credentials")
    with st.form(key='my_form'):
        if 'email' in st.session_state:
            email_input = st.text_input(label="E-Mail", placeholder="max.muster@gmail.com", value=st.session_state['email'])
        else:
            email_input = st.text_input(label="E-Mail", placeholder="max.muster@gmail.com")
        password_input = st.text_input(label="Password", placeholder="password", type="password")
        login_button = st.form_submit_button(label='Login')

    st.divider()
    st.title("Settings")
    page_width = st.slider(label="Page Width", min_value=600, max_value=2000, value=1100)

st.markdown(
        f"""
            <style>
                .appview-container .main .block-container{{ max-width: {page_width}px; }}
            </style>
        """,
        unsafe_allow_html=True,
    )

if login_button or ('email' in st.session_state):
    if 'email' not in st.session_state:
        st.session_state['email'] = email_input
        st.session_state["pw"] = password_input

    #---------------------------------------------------------------------------------------

    st.title('Evaluation of HR, Pace and Distance')
    st.text("This analysis is optimized for running, but it can also be applied to activities such as cycling or walking.\nPlease note that activities without distance and time information may not yield valid results.")
    # create two columnes to display the streamlit objects side by side
    col1, col2 = st.columns(2)
    with col1:
        startdate = st.date_input(label="Starting at:", value=date(2023, 2, 1), min_value=date(2020, 1, 1), max_value=date.today(), help='We will fetch all activities from the entry-date below "Starting at" until today')

    # Cache the loaded data so it does not have to make a login at Garmin on every Site refresh
    @st.cache_data(ttl=timedelta(hours=1))
    def load_data(mail, pw, startAt):
        activities = ga.garmin_api_get_all_activities_of_type(email=mail, password=pw, startdate=startAt)
        return pd.DataFrame(data=activities)
    
    try:
        with st.spinner('Connecting to Garmin ',):
            df = load_data(mail=st.session_state['email'], pw=st.session_state["pw"], startAt=startdate.strftime("%Y-%m-%d"))
    except Exception as e:
        st.error(f"Wrong credentials - Refresh page and try again\nError: {e}")
        st.stop()

    # create a datetime and date columne from the startTimeLocal of each activity for later plotting and calculations
    df['datetime'] = pd.to_datetime(df['startTimeLocal'])
    df['dates'] = df['datetime'].dt.date

    # write down the acivity type from the dict
    df["activityType"] = df['activityType'].str.get("typeKey")
    # get all saved activity types
    activitytypes_options = df["activityType"].unique()

    with col2:
        # create an list of all selected activities
        activitytypes = st.multiselect(label='Which activities do you want to check?',
                                    options=activitytypes_options,
                                    default=["running"],
                                    max_selections=1)

    if activitytypes != []:
        df = df.loc[df['activityType'].isin(activitytypes)]
    
        if activitytypes != ["indoor_cycling"]:
            df["distanceAdjElevation"] = df["distance"] + df["elevationGain"] * ELEVATION_CORRECTION_UP + df["elevationLoss"] * ELEVATION_CORRECTION_DOWN

            with col1:
                st.text("Do you want to correct for elevation gain/loss?  -->")
            with col2:
                corr_for_elevation = st.checkbox(label="Enable elevation-correction",
                                                help="""If the box is checked the distance will be corrected with the elevation gain and loss of each acitvity.\n
                                                        ELEVATION_CORRECTION_UP = + elevationGain * 4\n    ELEVATION_CORRECTION_DOWN = - elevationLoss * 2\n""")
                
            if corr_for_elevation:
                df["runningPace"] = (df["duration"] / 60) / (df["distanceAdjElevation"] / 1000)
            else:
                df["runningPace"] = (df["duration"] / 60) / (df["distance"] / 1000)
        else:
            df = df.loc[df['distance'] != 0]
            df["runningPace"] = (df["duration"] / 60) / (df["distance"] / 1000)

        st.divider()

        st.header("Filter")

        hr_filter_range = st.slider(label='Select a HR-range to filter', min_value=0, max_value=220, value=(118, 155))
        df = df.loc[(df['averageHR'] > hr_filter_range[0]) & (df['averageHR'] < hr_filter_range[1])]

        if activitytypes == ["running"]:
            pace_filter_range = st.slider(label='Select a Pace-range to filter', min_value=0.0, max_value=13.0, value=(4.8, 12.5))
            df = df.loc[(df['runningPace'] > pace_filter_range[0]) & (df['runningPace'] < pace_filter_range[1])]

        df.dropna(axis='columns', inplace=True)

        df.drop(labels=["ownerId","ownerDisplayName", "eventType",
                        "ownerFullName","ownerProfileImageUrlSmall",
                        "ownerProfileImageUrlMedium","ownerProfileImageUrlLarge","userRoles",
                        "privacy","summarizedDiveInfo","manufacturer",],axis='columns',inplace=True)


        x_dates = df["dates"]
        x_unix = (df['datetime'] - pd.Timestamp("1970-01-01")) // pd.Timedelta('1s')
        y_avarageHR = df["averageHR"]
        y_averageSpeed = df["runningPace"]
        if activitytypes != ["indoor_cycling"]:
            if corr_for_elevation:
                y_distance = df["distanceAdjElevation"] / 1000
            else:
                y_distance = df["distance"] / 1000
        else:
            y_distance = df["distance"] / 1000    

        #df.to_excel(excel_writer="output.xlsx")  

        # fig1, ax1 = plt.subplots()
        # ax1.legend(args="Avarage HR", loc="upper left")

        fig, ax  = plt.subplots(ncols=1, nrows=3, sharex=True, figsize=(10,7.5), dpi=300)

        # make a dot plot for avarage HR
        ax[0].scatter(x_dates, y_avarageHR, color="blue")
        # Set the limits for y axis
        ax[0].set_ylim(bottom=y_avarageHR.min()-5,top=y_avarageHR.max()+5)
        # Set the grid on major and minor
        ax[0].grid(visible=True, which="both")
        # Rotate x-axis labels by 45 degrees
        ax[0].tick_params(axis="x", rotation=45)
        # calc fit and plot 
        z = np.polyfit(x_unix, y_avarageHR, 1)
        p = np.poly1d(z)
        ax[0].plot(x_dates,p(x_unix),"r--")
        # labeling and legend
        ax[0].set_ylabel(ylabel="Avarage HR [ppm]")
        ax[0].legend(["Avarage HR", "Lineare Regression"], loc="upper left")


        ax[1].scatter(x_dates,y_averageSpeed, color="green")
        # Set the limits for y axis
        ax[1].set_ylim(bottom=y_averageSpeed.min()-0.2,top=y_averageSpeed.max()+0.2)
        # Set the grid on major and minor
        ax[1].grid(visible=True, which="both")
        # Rotate x-axis labels by 45 degrees
        ax[1].tick_params(axis="x", rotation=45)
        # calc fit and plot 
        z = np.polyfit(x_unix, y_averageSpeed, 1)
        p = np.poly1d(z)
        ax[1].plot(x_dates,p(x_unix),"r--")
        # labeling and legend
        ax[1].set_ylabel(ylabel="Avarage Pace [min/km]")
        ax[1].legend(["Avarage Pace", "Lineare Regression"], loc="upper left")


        ax[2].scatter(x_dates,y_distance, color="orange")
        # Set the limits for y axis
        ax[2].set_ylim(bottom=y_distance.min()-0.5,top=y_distance.max()+0.5)
        # Set the grid on major and minor
        ax[2].grid(visible=True, which="both")
        # Rotate x-axis labels by 45 degrees
        ax[2].tick_params(axis="x", rotation=45)
        # calc fit and plot 
        z = np.polyfit(x_unix, y_distance, 1)
        p = np.poly1d(z)
        ax[2].plot(x_dates,p(x_unix),"r--")
        # labeling and legend
        ax[2].set_ylabel(ylabel="Distance [km]")
        ax[2].legend(["Distance", "Lineare Regression"], loc="upper left")

        fig.set_figheight(9)

        st.pyplot(fig)
        st.divider()

        # Create column with YYYY-WW (year-calenderweek) time-stamp
        df["year_week"] = pd.to_datetime(df['startTimeLocal']).dt.strftime('%Y-%U')
        # Get the sum of meters run in every week
        weekly_volume = df[["year_week","distance"]].groupby(by=["year_week"] ).sum()
        # get kilometers instead of meters
        weekly_volume["distance"] = weekly_volume["distance"] / 1000
        st.subheader("Weekly Volume")
        st.text("Weekly volume in kilometers for running is the sum distance a runner travels over the course of a week, indicating their training intensity and endurance level. It's a key metric in assessing a runners overall running progress and fitness.")
        st.bar_chart(weekly_volume)

        st.divider()

        st.subheader("Scatterplot")
        st.text("Below is a scatterplot depicting the data for Heart Rate, Pace, and Distance.\nEach dot's size corresponds to the distance, while the color scheme represents the pace.\nThe y-axis represents Heart Rate.")
        # https://plotly.com/python-api-reference/generated/plotly.express.scatter.html
        # https://plotly.com/python/axes/#set-number-of-tick-marks-and-grid-lines
        if activitytypes == ["running"]:
            if corr_for_elevation:
                fig_plotly = px.scatter(data_frame=df, x="dates", y="averageHR", size="distanceAdjElevation",
                                        color='runningPace', color_continuous_scale='Bluered_r',
                                        labels=dict(dates="", runningPace="Pace [min/km]", averageHR="Average HR [ppm]", distanceAdjElevation="Distance [m]"))
            else:
                fig_plotly = px.scatter(data_frame=df, x="dates", y="averageHR", size="distance",
                                color='runningPace', color_continuous_scale='Bluered_r',
                                labels=dict(dates="", runningPace="Pace [min/km]", averageHR="Average HR [ppm]", distanceAdjElevation="Distance [m]"))
        else:
            fig_plotly = px.scatter(data_frame=df, x="dates", y="averageHR", size="distance",
                                color='runningPace', color_continuous_scale='Bluered_r',
                                labels=dict(dates="", runningPace="Pace [min/km]", averageHR="Average HR [ppm]", distanceAdjElevation="Distance [m]"))
            
        fig_plotly.update_xaxes(tickangle=-45,showticklabels=True, showgrid=True)

        st.plotly_chart(fig_plotly, use_container_width=True)

        st.title('Raw Table')
        st.text("disabled for now...")
        #st.table(df)


        logging.info('Stopped')

else:
    st.warning("Please login with your Garmin credentials")