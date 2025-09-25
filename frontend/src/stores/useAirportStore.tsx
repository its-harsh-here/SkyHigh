// src/stores/useAirportStore.ts
import { create } from 'zustand';

export interface AirportState {
    departureAirport: string;
    arrivalAirport: string;
    cruiseSpeed: number | '';
    departureTimeUTC: string; // ISO string
    waypoints: string[]; // ICAO codes array
    setDepartureAirport: (icao: string) => void;
    setArrivalAirport: (icao: string) => void;
    setCruiseSpeed: (speed: number | '') => void;
    setDepartureTimeUTC: (time: string) => void;
    setWaypoints: (wps: string[]) => void;

    reset: () => void;
}

const useAirportStore = create<AirportState>((set) => ({
    departureAirport: '',
    arrivalAirport: '',
    cruiseSpeed: 450,
    departureTimeUTC: new Date().toISOString(),
    waypoints: [],
    setDepartureAirport: (icao) => set({ departureAirport: icao.toUpperCase() }),
    setArrivalAirport: (icao) => set({ arrivalAirport: icao.toUpperCase() }),
    setCruiseSpeed: (speed) => set({ cruiseSpeed: speed }),
    setDepartureTimeUTC: (time) => set({ departureTimeUTC: time }),
    setWaypoints: (wps) => set({ waypoints: wps.map(w => w.toUpperCase()) }),
    
    reset: () =>
        set({
            departureAirport: '',
            arrivalAirport: '',
            cruiseSpeed: 450,
            departureTimeUTC: new Date().toISOString(),
            waypoints: [],
        }),
}));

export default useAirportStore;
