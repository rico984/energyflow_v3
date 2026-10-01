import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from inverter_model import Inputs, simulate

st.set_page_config(page_title='Hybrid-Inverter Simulator',page_icon='⚡',layout='wide')
st.title('⚡ SENEC.HOME V3 hybrid Leistungsfluss-Simulator')
st.caption('Näherungsmodell. AC positiv = Einspeisung, AC negativ = Netzbezug; Batterie positiv = Entladung.')

with st.sidebar:
 st.header('Gerätekonfiguration')
 variant=st.selectbox('Batterievariante',['10,0 kWh','5,0 kWh'])
 dc,dd=(2500,3750) if variant.startswith('10') else (1250,2500)
 charge_dev=st.number_input('Max. DC-Ladeleistung [W]',0,5000,dc,50)
 discharge_dev=st.number_input('Max. DC-Entladeleistung [W]',0,5000,dd,50)
 pvmax=st.number_input('Simulierte PV-DC-Grenze [W]',0,20000,7500,100)
 st.subheader('Modellannahmen')
 ep=st.slider('Wirkungsgrad PV → AC',.80,1.0,.97,.01)
 eb=st.slider('Wirkungsgrad Batterie → AC',.80,1.0,.95,.01)
 ea=st.slider('Wirkungsgrad AC → Batterie',.80,1.0,.94,.01)
 taper=st.slider('Spannungs-Abregelzone [V]',0.,2.,.5,.1)
 st.subheader('SOC-Grenzen')
 soc_min=st.number_input('Minimaler SOC [%]',0.,100.,5.,1.)
 soc_max=st.number_input('Maximaler SOC [%]',0.,100.,95.,1.)
 soc_taper=st.slider('SOC-Abregelzone [%]',0.,20.,5.,1.)
 st.subheader('Temperaturgrenzen')
 charge_tmin=st.number_input('Laden min. [°C]',-30.,30.,0.,1.)
 charge_tmax=st.number_input('Laden max. [°C]',0.,70.,45.,1.)
 discharge_tmin=st.number_input('Entladen min. [°C]',-30.,30.,-10.,1.)
 discharge_tmax=st.number_input('Entladen max. [°C]',0.,80.,50.,1.)
 temp_taper=st.slider('Temperatur-Abregelzone [K]',0.,15.,5.,1.)
 st.info('Näherungsmodell. Rampen, Filter und Firmware-Hysterese sind nicht modelliert.')

def make_inputs(pac,pv1,pv2,u,pcharge,pdis,umin,umax,icharge,idis,soc,temp,bms_c,bms_d,bms_ic,bms_id,exact=False,suppress_export=False):
 return Inputs(pac,pcharge,pdis,umax,umin,icharge,idis,u,pv1,pv2,charge_dev,discharge_dev,pvmax,ep,eb,ea,taper,soc,soc_min,soc_max,soc_taper,temp,charge_tmin,charge_tmax,discharge_tmin,discharge_tmax,temp_taper,bms_c,bms_d,bms_ic,bms_id,exact,suppress_export)

def time_in_window(current, start, end):
 # Gleiche Start-/Endzeit bedeutet deaktivierte Dauer; Zeitfenster über Mitternacht werden unterstützt.
 if start == end: return False
 return start <= current < end if start < end else current >= start or current < end

def active_schedule(current, schedules):
 for index,item in enumerate(schedules,1):
  if item['enabled'] and time_in_window(current,item['start'],item['end']):
   return index,item
 return None,None

tab1,tab2=st.tabs(['Betriebspunkt','Dynamisches Szenario'])
with tab1:
 a,b=st.columns(2)
 with a:
  st.subheader('Schreibbare Parameter')
  pac=st.slider('Pac_set [W]',-3700,4600,2000,50)
  pcharge=st.slider('Pac_charge_max [W]',-3700,0,-3700,50)
  pdis=st.slider('Pac_discharge_max [W]',0,4600,4600,50)
  c1,c2=st.columns(2)
  with c1:
   umin=st.number_input('U_bat_set_min [mV]',42000,65000,44000,100)
   icharge=st.number_input('I_bat_charge_max [mA]',-75000,0,-50000,1000)
  with c2:
   umax=st.number_input('U_bat_set_max [mV]',42000,65000,58000,100)
   idis=st.number_input('I_bat_discharge_max [mA]',0,75000,50000,1000)
  if umin>=umax: st.warning('U_bat_set_min sollte kleiner als U_bat_set_max sein.')
 with b:
  st.subheader('Aktuelle DC-Werte')
  u=st.slider('Ubat [V]',42.,65.,51.2,.1)
  soc=st.slider('SOC [%]',0.,100.,50.,1.)
  temp=st.slider('Batterietemperatur [°C]',-30.,80.,25.,1.)
  pv1=st.slider('PV MPPT 1 [W]',0,7500,1500,50)
  pv2=st.slider('PV MPPT 2 [W]',0,7500,1200,50)
  upv=st.slider('Upv zur Stromprüfung [V]',75,650,350,5)
  st.subheader('BMS-Status')
  bms_c=st.checkbox('Laden freigegeben',True)
  bms_d=st.checkbox('Entladen freigegeben',True)
  bc1,bc2=st.columns(2)
  with bc1: bms_ic=st.number_input('BMS max. Ladestrom [mA]',0,100000,60000,1000)
  with bc2: bms_id=st.number_input('BMS max. Entladestrom [mA]',0,100000,60000,1000)
  st.write(f'Ipv1: **{pv1/upv:.2f} A**, Ipv2: **{pv2/upv:.2f} A**')
  if pv1/upv>20 or pv2/upv>20: st.warning('Mindestens ein MPPT überschreitet rechnerisch 20 A.')
 r=simulate(make_inputs(pac,pv1,pv2,u,pcharge,pdis,umin,umax,icharge,idis,soc,temp,bms_c,bms_d,bms_ic,bms_id))
 st.divider(); st.subheader('Berechneter Betriebspunkt')
 cols=st.columns(6)
 curtailed_pct=100*r.curtailed/r.pv_raw if r.pv_raw else 0
 for col,label,val in zip(cols,['PV verfügbar','PV genutzt','AC-Leistung','Batterieleistung','Batteriestrom','PV abgeregelt'],[r.pv_raw,r.pv_used,r.p_ac,r.p_bat,r.i_bat_ma,r.curtailed]): col.metric(label,f'{val:,.0f} '+('mA' if label=='Batteriestrom' else 'W'))
 st.caption(f'Abregelquote: **{curtailed_pct:.1f} %** der aktuell verfügbaren PV-Leistung')
 left,right=st.columns([1.5,1])
 with left:
  labels=['MPPT 1','MPPT 2','Inverter','Batterie','AC-Netz','Verluste','Abregelung']; s=[];t=[];v=[];colors=[]
  def flow(a,b,q,color):
   if q>.5: s.append(a);t.append(b);v.append(q);colors.append(color)
  ratio=r.pv_used/r.pv_raw if r.pv_raw else 0
  flow(0,2,pv1*ratio,'rgba(255,193,7,.7)');flow(1,2,pv2*ratio,'rgba(255,193,7,.7)')
  flow(0,6,pv1*(1-ratio),'rgba(120,120,120,.5)');flow(1,6,pv2*(1-ratio),'rgba(120,120,120,.5)')
  flow(3,2,r.p_bat,'rgba(255,127,14,.7)') if r.p_bat>0 else flow(2,3,-r.p_bat,'rgba(31,119,180,.7)')
  flow(2,4,r.p_ac,'rgba(44,160,44,.7)') if r.p_ac>=0 else flow(4,2,-r.p_ac,'rgba(31,119,180,.7)')
  flow(2,5,r.losses,'rgba(214,39,40,.6)')
  fig=go.Figure(go.Sankey(node=dict(label=labels,pad=18,thickness=22),link=dict(source=s,target=t,value=v,color=colors)))
  fig.update_layout(title='Leistungsfluss [W]',height=460,margin=dict(l=10,r=10,t=45,b=10));st.plotly_chart(fig,use_container_width=True)
 with right:
  g=go.Figure(go.Indicator(mode='gauge+number+delta',value=r.p_ac,delta={'reference':pac},title={'text':'AC-Leistung [W]'},gauge={'axis':{'range':[-4600,4600]},'threshold':{'line':{'color':'red','width':4},'value':pac}}))
  g.update_layout(height=300);st.plotly_chart(g,use_container_width=True)
  st.write(f'Ladegrenze: **{r.charge_limit:,.0f} W**')
  st.write(f'Entladegrenze: **{r.discharge_limit:,.0f} W**')
  st.write(f'Verluste: **{r.losses:,.0f} W**')
 st.subheader('Regelungsstatus')
 for msg in r.status:
  st.success(msg) if 'ohne aktive' in msg else st.warning(msg)
 df=pd.DataFrame([{'Pac_set_W':pac,'P_AC_W':r.p_ac,'P_PV_W':r.pv_raw,'P_Bat_W':r.p_bat,'I_Bat_mA':r.i_bat_ma,'U_Bat_V':u,'SOC_Prozent':soc,'Batterietemperatur_C':temp,'BMS_Laden':bms_c,'BMS_Entladen':bms_d,'PV_genutzt_W':r.pv_used,'Abregelung_W':r.curtailed,'Abregelquote_Prozent':curtailed_pct,'Status':' | '.join(r.status)}])
 st.download_button('Betriebspunkt als CSV',df.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'betriebspunkt.csv','text/csv')

with tab2:
 st.subheader('Zeitabhängige Simulation')
 c1,c2,c3=st.columns(3)
 with c1:
  duration_h=st.slider('Simulationsdauer [h]',1,72,24,1,help='Maximal 72 Stunden beziehungsweise 3 Tage')
  resolution_min=st.select_slider('Zeitliche Auflösung [min]',options=[1,2,5,10,15,30,60],value=10)
  peak=st.number_input('PV-Maximum [W]',0,15000,6000,100)
 with c2: p0=st.number_input('Pac_set Start [W]',-3700,4600,1000,100); p1=st.number_input('Pac_set Ende [W]',-3700,4600,3000,100)
 with c3: u0=st.number_input('Ubat Start [V]',42.,65.,50.,.1); u1=st.number_input('Ubat Ende [V]',42.,65.,57.9,.1)
 d1,d2=st.columns(2)
 with d1: soc0=st.number_input('SOC Start [%]',0.,100.,30.,1.); soc1=st.number_input('SOC Ende [%]',0.,100.,96.,1.)
 with d2: temp0=st.number_input('Temperatur Start [°C]',-30.,80.,25.,1.); temp1=st.number_input('Temperatur Ende [°C]',-30.,80.,43.,1.)
 start_time=st.date_input('Startdatum')
 start_clock=st.time_input('Startzeit')
 start_dt=pd.Timestamp.combine(start_time,start_clock)
 st.subheader('AC-Fahrplan mit drei täglichen Zeitfenstern')
 st.caption('Positive Werte fordern Einspeisung, negative Werte Netzbezug. Zeitfenster dürfen über Mitternacht laufen. Bei Überschneidung hat Zeitfenster 1 vor 2 vor 3 Vorrang.')
 schedules=[]
 schedule_cols=st.columns(3)
 defaults=[('06:00','09:00',1500),('12:00','14:00',-1500),('18:00','22:00',2500)]
 for idx,col in enumerate(schedule_cols):
  with col:
   st.markdown(f'**Zeitfenster {idx+1}**')
   enabled=st.checkbox('Aktiv',True,key=f'schedule_enabled_{idx}')
   sh,sm=map(int,defaults[idx][0].split(':')); eh,em=map(int,defaults[idx][1].split(':'))
   start=st.time_input('Start',value=pd.Timestamp(2000,1,1,sh,sm).time(),key=f'schedule_start_{idx}',step=300)
   end=st.time_input('Ende',value=pd.Timestamp(2000,1,1,eh,em).time(),key=f'schedule_end_{idx}',step=300)
   power=st.number_input('Statische AC-Leistung [W]',-3700,4600,defaults[idx][2],50,key=f'schedule_power_{idx}')
   schedules.append({'enabled':enabled,'start':start,'end':end,'power':power})
 duration_min=duration_h*60
 steps=int(duration_min/resolution_min)+1
 st.caption(f'Berechnung mit **{steps:,} Stützpunkten** über **{duration_h} Stunden** bei **{resolution_min} Minuten** Auflösung.')
 rows=[]
 for i in range(steps):
  elapsed_min=min(i*resolution_min,duration_min)
  x=elapsed_min/duration_min if duration_min else 0
  timestamp=start_dt+pd.Timedelta(minutes=elapsed_min)
  hour_of_day=timestamp.hour+timestamp.minute/60
  daylight=max(0.0,math.sin(math.pi*(hour_of_day-6)/12))
  pv=peak*daylight
  fallback_ps=p0+(p1-p0)*x
  schedule_no,schedule=active_schedule(timestamp.time(),schedules)
  ps=schedule['power'] if schedule else fallback_ps
  exact=schedule is not None
  suppress_export=exact and ps < 0
  uv=u0+(u1-u0)*x;sv=soc0+(soc1-soc0)*x;tv=temp0+(temp1-temp0)*x
  rr=simulate(make_inputs(ps,pv*.55,pv*.45,uv,-3700,4600,44000,58000,-50000,50000,sv,tv,True,True,60000,60000,exact,suppress_export))
  rows.append({'Zeitpunkt':timestamp,'Vergangene Zeit [h]':elapsed_min/60,'Aktives Zeitfenster':schedule_no or 0,'PV [W]':rr.pv_raw,'AC [W]':rr.p_ac,'Pac_set [W]':ps,'Batterie [W]':rr.p_bat,'Abregelung [W]':rr.curtailed,'Ubat [V]':uv,'SOC [%]':sv,'Temperatur [°C]':tv,'PV genutzt [W]':rr.pv_used,'Status':' | '.join(rr.status)})
 dyn=pd.DataFrame(rows); fig=go.Figure()
 for name,color,dash in [('PV [W]','#F1C40F','solid'),('AC [W]','#27AE60','solid'),('Pac_set [W]','#2C3E50','dash'),('Batterie [W]','#2980B9','solid'),('Abregelung [W]','#E74C3C','solid')]: fig.add_trace(go.Scatter(x=dyn['Zeitpunkt'],y=dyn[name],name=name,line=dict(color=color,dash=dash)))
 scheduled_points=int((dyn['Aktives Zeitfenster']>0).sum())
 curtailed_energy=(dyn['Abregelung [W]'].sum()*resolution_min/60)/1000
 st.caption(f'Aktive Fahrplanpunkte: **{scheduled_points}** | Abgeregelte PV-Energie im dargestellten Zeitraum: **{curtailed_energy:.2f} kWh**')
 fig.add_hline(y=0,line_color='gray');fig.update_layout(height=520,hovermode='x unified',xaxis_title='Datum und Uhrzeit',yaxis_title='Leistung [W]');st.plotly_chart(fig,use_container_width=True)
 st.download_button('Szenario als CSV',dyn.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'szenario.csv','text/csv')

with st.expander('Modellannahmen'):
 st.markdown('''- PV deckt zuerst einen positiven AC-Sollwert.
- Fehlende AC-Leistung wird aus der Batterie ergänzt.
- PV-Überschuss lädt zuerst die Batterie und wird danach bis zur AC-Grenze eingespeist.
- Ein negativer Pac_set fordert Netzbezug zum Laden an.
- Strom-, Spannungs-, Geräte- und AC-Grenzen werden kombiniert.
- Spannungs-, SOC- und Temperaturgrenzen regeln innerhalb der eingestellten Fenster linear ab.
- BMS-Freigaben wirken als harte Sperre; BMS-Stromgrenzen begrenzen vor den Geräte-Leistungsgrenzen.
- Abgeregelte PV-Leistung wird als Differenz aus verfügbarer und tatsächlich genutzter PV-Leistung ausgewiesen.
- In aktiven Fahrplanfenstern ist Pac_set ein exakter AC-Zielwert. Bei positiver Vorgabe darf Energiemangel den Istwert reduzieren.
- Bei negativer Fahrplanvorgabe wird keine PV-Leistung eingespeist; nicht speicherbare PV-Leistung wird abgeregelt.''')
