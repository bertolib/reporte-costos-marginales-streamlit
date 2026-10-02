"""Static electrical-node catalog for the first Excel-backed iteration."""

from src.domain.entities import ElectricalNode


NODE_CATALOG: dict[str, ElectricalNode] = {
    "cmg_mej_110": ElectricalNode(
        node_id="cmg_mej_110",
        name="Mejillones 110",
        zone="Norte",
        voltage_kv=110,
    ),
    "cmg_chacaya_110": ElectricalNode(
        node_id="cmg_chacaya_110",
        name="Chacaya 110",
        zone="Norte",
        voltage_kv=110,
    ),
    "cmg_chaca_110_clp": ElectricalNode(
        node_id="cmg_chaca_110_clp",
        name="Chaca 110",
        zone="Norte",
        voltage_kv=110,
    ),
    "alto_jahuel_220": ElectricalNode(
        node_id="alto_jahuel_220",
        name="Alto Jahuel 220",
        zone="Centro",
        voltage_kv=220,
    ),
    "charrua_220": ElectricalNode(
        node_id="charrua_220",
        name="Charrua 220",
        zone="Sur",
        voltage_kv=220,
    ),
}


EXCEL_NODE_COLUMNS = {
    "Cmg Mej 110 (USD/MWh)": "cmg_mej_110",
    "Cmg Chacaya 110 (USD/MWh)": "cmg_chacaya_110",
    "Alto Jahuel 220 (USD/MWh)": "alto_jahuel_220",
    "Charrua 220 (USD/MWh)": "charrua_220",
}
