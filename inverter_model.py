from dataclasses import dataclass, field
from typing import List

@dataclass
class Inputs:
    pac_set: float=2000
    pac_charge_max: float=-3700
    pac_discharge_max: float=4600
    u_max_mv: float=58000
    u_min_mv: float=44000
    i_charge_max_ma: float=-50000
    i_discharge_max_ma: float=50000
    u_bat: float=51.2
    pv1: float=1500
    pv2: float=1200
    charge_device_max: float=2500
    discharge_device_max: float=3750
    pv_dc_max: float=7500
    eta_pv_ac: float=.97
    eta_bat_ac: float=.95
    eta_ac_bat: float=.94
    taper_v: float=.5
    soc_percent: float=50.0
    soc_min_percent: float=5.0
    soc_max_percent: float=95.0
    soc_taper_percent: float=5.0
    battery_temp_c: float=25.0
    charge_temp_min_c: float=0.0
    charge_temp_max_c: float=45.0
    discharge_temp_min_c: float=-10.0
    discharge_temp_max_c: float=50.0
    temp_taper_c: float=5.0
    bms_charge_enabled: bool=True
    bms_discharge_enabled: bool=True
    bms_charge_current_max_ma: float=60000.0
    bms_discharge_current_max_ma: float=60000.0
    exact_ac_target: bool=False
    suppress_pv_export_on_import: bool=False

@dataclass
class Result:
    pv_raw: float; pv_used: float; curtailed: float; p_bat: float
    i_bat_ma: float; p_ac: float; losses: float
    charge_limit: float; discharge_limit: float
    status: List[str]=field(default_factory=list)

def clamp(x, lo, hi): return max(lo, min(hi, x))

def taper_charge(u, limit, window):
    if u >= limit: return 0.0
    if window <= 0 or u <= limit-window: return 1.0
    return clamp((limit-u)/window, 0, 1)

def taper_discharge(u, limit, window):
    if u <= limit: return 0.0
    if window <= 0 or u >= limit+window: return 1.0
    return clamp((u-limit)/window, 0, 1)

def window_factor(value, minimum, maximum, taper):
    if value <= minimum or value >= maximum: return 0.0
    if taper <= 0: return 1.0
    low = clamp((value-minimum)/taper, 0, 1)
    high = clamp((maximum-value)/taper, 0, 1)
    return min(low, high)

def simulate(x: Inputs):
    status=[]; u=max(.1,x.u_bat)
    ep=clamp(x.eta_pv_ac,.01,1); eb=clamp(x.eta_bat_ac,.01,1); ea=clamp(x.eta_ac_bat,.01,1)
    raw=max(0,x.pv1)+max(0,x.pv2); pv=min(raw,max(0,x.pv_dc_max))
    if raw>pv+.5: status.append('PV-DC-Grenze erreicht')
    voltage_cf=taper_charge(u,x.u_max_mv/1000,x.taper_v)
    voltage_df=taper_discharge(u,x.u_min_mv/1000,x.taper_v)
    soc_cf=taper_charge(x.soc_percent,x.soc_max_percent,x.soc_taper_percent)
    soc_df=taper_discharge(x.soc_percent,x.soc_min_percent,x.soc_taper_percent)
    temp_cf=window_factor(x.battery_temp_c,x.charge_temp_min_c,x.charge_temp_max_c,x.temp_taper_c)
    temp_df=window_factor(x.battery_temp_c,x.discharge_temp_min_c,x.discharge_temp_max_c,x.temp_taper_c)
    bms_cf=1.0 if x.bms_charge_enabled else 0.0
    bms_df=1.0 if x.bms_discharge_enabled else 0.0
    cf=min(voltage_cf,soc_cf,temp_cf,bms_cf)
    df=min(voltage_df,soc_df,temp_df,bms_df)
    charge_current=min(abs(min(0,x.i_charge_max_ma)),max(0,x.bms_charge_current_max_ma))
    discharge_current=min(max(0,x.i_discharge_max_ma),max(0,x.bms_discharge_current_max_ma))
    cl=min(u*charge_current/1000,max(0,x.charge_device_max))*cf
    dl=min(u*discharge_current/1000,max(0,x.discharge_device_max))*df
    if voltage_cf==0: status.append('Laden durch obere Spannungsgrenze gesperrt')
    elif voltage_cf<1: status.append('Ladestrom an oberer Spannungsgrenze abgeregelt')
    if voltage_df==0: status.append('Entladen durch untere Spannungsgrenze gesperrt')
    elif voltage_df<1: status.append('Entladestrom an unterer Spannungsgrenze abgeregelt')
    if soc_cf==0: status.append('Laden durch maximalen SOC gesperrt')
    elif soc_cf<1: status.append('Ladeleistung nahe maximalem SOC abgeregelt')
    if soc_df==0: status.append('Entladen durch minimalen SOC gesperrt')
    elif soc_df<1: status.append('Entladeleistung nahe minimalem SOC abgeregelt')
    if temp_cf==0: status.append('Laden durch BMS-Temperaturgrenze gesperrt')
    elif temp_cf<1: status.append('Ladeleistung temperaturbedingt abgeregelt')
    if temp_df==0: status.append('Entladen durch BMS-Temperaturgrenze gesperrt')
    elif temp_df<1: status.append('Entladeleistung temperaturbedingt abgeregelt')
    if not x.bms_charge_enabled: status.append('BMS-Ladefreigabe fehlt')
    if not x.bms_discharge_enabled: status.append('BMS-Entladefreigabe fehlt')
    if charge_current < abs(min(0,x.i_charge_max_ma)): status.append('Ladestrom durch BMS-Stromgrenze begrenzt')
    if discharge_current < max(0,x.i_discharge_max_ma): status.append('Entladestrom durch BMS-Stromgrenze begrenzt')
    export=min(4600,max(0,x.pac_discharge_max)); imp=min(4600,abs(min(0,x.pac_charge_max)))
    target=clamp(x.pac_set,-imp,export)
    if target!=x.pac_set: status.append('Pac_set durch AC-Grenze begrenzt')
    used=0.; bat=0.; ac=0.
    if target>=0:
        q=min(pv,target/ep); used+=q; ac+=q*ep
        need=max(0,target-ac)/eb; q=min(dl,need); bat+=q; ac+=q*eb
        if ac<target-.5: status.append('AC-Sollwert wegen Entladegrenze nicht erreicht')
        rem=pv-used; q=min(cl,rem); bat-=q; used+=q
        if rem>cl+.5: status.append('Batterie-Ladegrenze erreicht')
        rem=pv-used
        export_ceiling=target if x.exact_ac_target else export
        q=min(rem,max(0,export_ceiling-ac)/ep); used+=q; ac+=q*ep
    else:
        q=min(pv,cl); used+=q; bat-=q
        capacity=max(0,cl-q); requested=abs(target)
        grid=min(requested,imp,capacity/ea); ac=-grid; bat-=grid*ea
        if grid<requested-.5: status.append('Netz-Ladesollwert begrenzt')
        rem=pv-used
        if not x.suppress_pv_export_on_import:
            q=min(rem,max(0,export-ac)/ep); used+=q; ac+=q*ep
        elif rem > 0.5:
            status.append('PV-Einspeisung im Netzbezugs-Zeitfenster gesperrt')
    ac=clamp(ac,-imp,export); curtailed=max(0,raw-used)
    if curtailed>.5: status.append('PV-Überschuss wird abgeregelt')
    sources=used+max(0,bat)+max(0,-ac); sinks=max(0,ac)+max(0,-bat)
    losses=max(0,sources-sinks); current=bat/u*1000
    if not status: status=['Betriebspunkt ohne aktive Begrenzung']
    return Result(raw,used,curtailed,bat,current,ac,losses,cl,dl,status)
