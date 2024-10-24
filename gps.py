import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, find_peaks
from scipy.fftpack import fft
from geopy.distance import geodesic
import streamlit as st
import folium
from streamlit_folium import st_folium

excel_file = './data/gps.xls'
acc_data = pd.read_excel(excel_file, sheet_name='Linear Acceleration')
gps_data = pd.read_excel(excel_file, sheet_name='Location')

time = acc_data['Time (s)']
acc_z = acc_data['Linear Acceleration z (m/s^2)']
acc_x = acc_data['Linear Acceleration x (m/s^2)']
acc_y = acc_data['Linear Acceleration y (m/s^2)']

lat = gps_data['Latitude (°)']
lon = gps_data['Longitude (°)']
height = gps_data['Height (m)']
velocity = gps_data['Velocity (m/s)']
horizontal_accuracy = gps_data['Horizontal Accuracy (m)']
vertical_accuracy = gps_data['Vertical Accuracy (m)']
direction = gps_data['Direction (°)']

def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y

fs = 50
filtered_acc_z = lowpass_filter(acc_z, cutoff=0.3, fs=fs)
peaks, _ = find_peaks(filtered_acc_z, height=0.1)
steps_count_filtered = len(peaks)

N = len(filtered_acc_z)
T = time[1] - time[0]  
yf = fft(filtered_acc_z)
xf = np.linspace(0.0, 1.0/(2.0*T), N//2)

dominant_frequency = xf[np.argmax(np.abs(yf[:N//2]))]
steps_count_fft = dominant_frequency * (time.iloc[-1] - time.iloc[0])

total_distance = 0
for i in range(1, len(lat)):
    coords_1 = (lat[i-1], lon[i-1])
    coords_2 = (lat[i], lon[i])
    distance = geodesic(coords_1, coords_2).meters
    if horizontal_accuracy[i] <= 5:  
        total_distance += distance
average_speed = velocity.mean()
step_length = total_distance / steps_count_filtered if steps_count_filtered > 0 else 0

st.title("Urheilusovellusprototyyppi - Analyysi ja visualisointi")
st.write(f"Askelmäärä (suodatetusta kiihtyvyysdatasta): {steps_count_filtered}")
st.write(f"Askelmäärä (Fourier-analyysin perusteella): {int(steps_count_fft)}")
st.write(f"Keskinopeus: {average_speed:.2f} m/s")
st.write(f"Matka: {total_distance:.2f} metriä")
st.write(f"Askelpituus: {step_length:.2f} metriä")
st.write("Suodatettu kiihtyvyysdata (z-komponentti):")
st.line_chart(filtered_acc_z)

psd = 2.0/N * np.abs(yf[:N//2])
chart_data = pd.DataFrame({'freq': xf, 'psd': psd})
st.write("Tehospektritiheys (z-komponentti):")
st.line_chart(chart_data.set_index('freq'))

st.write("Reittisi kartalla:")
m = folium.Map(location=[lat.mean(), lon.mean()], zoom_start=15)
folium.PolyLine(locations=list(zip(lat, lon)), color='blue', weight=1).add_to(m)
folium.Marker(location=[lat.iloc[0], lon.iloc[0]], popup='Start', icon=folium.Icon(color='green')).add_to(m)
folium.Marker(location=[lat.iloc[-1], lon.iloc[-1]], popup='End', icon=folium.Icon(color='red')).add_to(m)

for i in range(len(lat)):
    folium.Circle(
        location=(lat[i], lon[i]),
        radius=1, 
        color='blue',
        fill=True,
        fill_opacity=0.1,
        popup=f'Accuracy: {horizontal_accuracy[i]} m'
    ).add_to(m)
st_folium(m, width=700)