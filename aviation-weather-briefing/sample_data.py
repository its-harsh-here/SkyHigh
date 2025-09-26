"""
Sample data for testing the Aviation Weather Briefing System
This provides mock data when live API calls are not available
"""

SAMPLE_METAR_DATA = {
    'KJFK': {
        'raw_text': 'KJFK 261851Z 28012G18KT 10SM FEW250 22/16 A3012 RMK AO2 SLP201 T02220161',
        'station_id': 'KJFK',
        'observation_time': '2024-09-26T18:51:00Z',
        'temperature': 22,
        'dewpoint': 16,
        'wind_direction': 280,
        'wind_speed': 12,
        'wind_gust': 18,
        'visibility': 10.0,
        'altimeter': 30.12,
        'flight_category': 'VFR',
        'clouds': [{'cover': 'FEW', 'base': 25000}],
        'weather_conditions': '',
        'ceiling': None
    },
    'KLAX': {
        'raw_text': 'KLAX 261853Z 25008KT 10SM CLR 26/18 A2995 RMK AO2 SLP140 T02610183',
        'station_id': 'KLAX',
        'observation_time': '2024-09-26T18:53:00Z',
        'temperature': 26,
        'dewpoint': 18,
        'wind_direction': 250,
        'wind_speed': 8,
        'wind_gust': None,
        'visibility': 10.0,
        'altimeter': 29.95,
        'flight_category': 'VFR',
        'clouds': [],
        'weather_conditions': '',
        'ceiling': None
    },
    'KORD': {
        'raw_text': 'KORD 261851Z 30015G22KT 5SM -RA BKN008 OVC015 18/16 A2998 RMK AO2 RAB35 SLP148 P0001 T01830161',
        'station_id': 'KORD',
        'observation_time': '2024-09-26T18:51:00Z',
        'temperature': 18,
        'dewpoint': 16,
        'wind_direction': 300,
        'wind_speed': 15,
        'wind_gust': 22,
        'visibility': 5.0,
        'altimeter': 29.98,
        'flight_category': 'IFR',
        'clouds': [{'cover': 'BKN', 'base': 800}, {'cover': 'OVC', 'base': 1500}],
        'weather_conditions': '-RA',
        'ceiling': 800
    },
    'KDEN': {
        'raw_text': 'KDEN 261852Z 24018G25KT 10SM FEW120 SCT180 BKN250 20/M02 A3025 RMK AO2 SLP228 T02001017',
        'station_id': 'KDEN',
        'observation_time': '2024-09-26T18:52:00Z',
        'temperature': 20,
        'dewpoint': -2,
        'wind_direction': 240,
        'wind_speed': 18,
        'wind_gust': 25,
        'visibility': 10.0,
        'altimeter': 30.25,
        'flight_category': 'VFR',
        'clouds': [{'cover': 'FEW', 'base': 12000}, {'cover': 'SCT', 'base': 18000}, {'cover': 'BKN', 'base': 25000}],
        'weather_conditions': '',
        'ceiling': None
    },
    'KATL': {
        'raw_text': 'KATL 261852Z 09008KT 10SM SCT250 24/18 A3008 RMK AO2 SLP180 T02440183',
        'station_id': 'KATL',
        'observation_time': '2024-09-26T18:52:00Z',
        'temperature': 24,
        'dewpoint': 18,
        'wind_direction': 90,
        'wind_speed': 8,
        'wind_gust': None,
        'visibility': 10.0,
        'altimeter': 30.08,
        'flight_category': 'VFR',
        'clouds': [{'cover': 'SCT', 'base': 25000}],
        'weather_conditions': '',
        'ceiling': None
    },
    'KDFW': {
        'raw_text': 'KDFW 261853Z 18015G22KT 8SM -TSRA BKN025 OVC040 25/22 A2995 RMK AO2 TSB40 SLP135 P0015 T02500222',
        'station_id': 'KDFW',
        'observation_time': '2024-09-26T18:53:00Z',
        'temperature': 25,
        'dewpoint': 22,
        'wind_direction': 180,
        'wind_speed': 15,
        'wind_gust': 22,
        'visibility': 8.0,
        'altimeter': 29.95,
        'flight_category': 'MVFR',
        'clouds': [{'cover': 'BKN', 'base': 2500}, {'cover': 'OVC', 'base': 4000}],
        'weather_conditions': '-TSRA',
        'ceiling': 2500
    },
    'KSEA': {
        'raw_text': 'KSEA 261853Z 21012KT 3SM BR BKN006 OVC012 16/15 A3015 RMK AO2 SLP210 T01610150',
        'station_id': 'KSEA',
        'observation_time': '2024-09-26T18:53:00Z',
        'temperature': 16,
        'dewpoint': 15,
        'wind_direction': 210,
        'wind_speed': 12,
        'wind_gust': None,
        'visibility': 3.0,
        'altimeter': 30.15,
        'flight_category': 'IFR',
        'clouds': [{'cover': 'BKN', 'base': 600}, {'cover': 'OVC', 'base': 1200}],
        'weather_conditions': 'BR',
        'ceiling': 600
    }
}

SAMPLE_TAF_DATA = {
    'KJFK': {
        'raw_text': 'KJFK 261720Z 2618/2724 28012G18KT P6SM FEW250 FM270200 30010KT P6SM SCT120 FM271000 32008KT P6SM BKN015 FM271800 28012G18KT P6SM FEW250',
        'station_id': 'KJFK',
        'issue_time': '2024-09-26T17:20:00Z',
        'valid_time_from': '2024-09-26T18:00:00Z',
        'valid_time_to': '2024-09-27T24:00:00Z',
        'forecasts': []
    }
}

SAMPLE_PIREP_DATA = {
    'KJFK': [
        {
            'raw_text': 'JFK UA /OV JFK090015/TM 1845/FL080/TP B737/SK BKN015/RM SMOOTH',
            'receipt_time': '2024-09-26T18:45:00Z',
            'observation_time': '2024-09-26T18:45:00Z',
            'aircraft_type': 'B737',
            'altitude': 8000,
            'turbulence': [],
            'icing': [],
            'visibility': None,
            'weather': [],
            'clouds': [{'cover': 'BKN', 'base': 1500}],
            'temperature': None
        }
    ]
}

def get_sample_weather_data(airport_code):
    """Get sample weather data for testing"""
    return {
        'metar': SAMPLE_METAR_DATA.get(airport_code),
        'taf': SAMPLE_TAF_DATA.get(airport_code),
        'pirep': SAMPLE_PIREP_DATA.get(airport_code, [])
    }
