from inverter_model import Inputs, simulate

def check():
    assert simulate(Inputs(pac_set=10000,pv1=10000,pv2=10000)).p_ac <= 4600.0001
    assert simulate(Inputs(u_bat=58,u_max_mv=58000,pv1=5000,pac_set=0)).p_bat >= -0.001
    assert simulate(Inputs(soc_percent=100,pv1=5000,pac_set=0)).p_bat >= -0.001
    assert simulate(Inputs(soc_percent=0,pv1=0,pac_set=2000)).p_bat <= 0.001
    assert simulate(Inputs(battery_temp_c=60,pv1=5000,pac_set=0)).p_bat >= -0.001
    assert simulate(Inputs(bms_discharge_enabled=False,pv1=0,pac_set=2000)).p_bat <= 0.001
    r=simulate(Inputs(pv1=10000,pv2=10000,pac_set=0,soc_percent=100))
    assert r.curtailed > 0

    # Exakter positiver Fahrplanwert: Überschuss darf den Sollwert nicht überschreiten.
    r=simulate(Inputs(pac_set=1000,pv1=7000,soc_percent=100,exact_ac_target=True))
    assert r.p_ac <= 1000.001 and r.curtailed > 0
    # Negativer Fahrplanwert bei voller Batterie: kein Export, gesamte PV wird abgeregelt.
    r=simulate(Inputs(pac_set=-1500,pv1=5000,soc_percent=100,exact_ac_target=True,suppress_pv_export_on_import=True))
    assert r.p_ac <= 0.001 and r.curtailed >= 4999
    # Positive Forderung darf bei fehlenden Quellen unterschritten werden.
    r=simulate(Inputs(pac_set=3000,pv1=500,discharge_device_max=0,exact_ac_target=True))
    assert r.p_ac < 3000
    print('Alle erweiterten Modelltests erfolgreich')

if __name__ == '__main__': check()
