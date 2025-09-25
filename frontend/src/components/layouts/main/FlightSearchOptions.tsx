import { useRef } from "react";
import useUIStore from "@/stores/useUIStore";
import useAirportStore from "@/stores/useAirportStore";
import { cn } from "@/lib/utils";

const FlightSearchOptions = () => {
    const departureRef = useRef<HTMLInputElement | null>(null);
    const arrivalRef = useRef<HTMLInputElement | null>(null);
    const cruiseSpeedRef = useRef<HTMLInputElement | null>(null);
    const waypointsRef = useRef<HTMLInputElement | null>(null);

    const departureAirport = useAirportStore((state) => state.departureAirport);
    const arrivalAirport = useAirportStore((state) => state.arrivalAirport);
    const cruiseSpeed = useAirportStore((state) => state.cruiseSpeed);
    const departureTimeUTC = useAirportStore((state) => state.departureTimeUTC);
    const waypoints = useAirportStore((state) => state.waypoints);

    const setDepartureAirport = useAirportStore((state) => state.setDepartureAirport);
    const setArrivalAirport = useAirportStore((state) => state.setArrivalAirport);
    const setCruiseSpeed = useAirportStore((state) => state.setCruiseSpeed);
    const setDepartureTimeUTC = useAirportStore((state) => state.setDepartureTimeUTC);
    const setWaypoints = useAirportStore((state) => state.setWaypoints);

    const loading = useUIStore((state) => state.loading);
    const setLoading = useUIStore((state) => state.setLoading);

    const handleWaypointsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const wps = e.target.value.split(",").map(w => w.trim()).filter(Boolean);
        setWaypoints(wps);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (loading) return;

        try {
            setLoading(true);

            const response = await fetch('/api/enhanced-flight-plan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    departure: departureAirport,
                    destination: arrivalAirport,
                    waypoints,
                    cruise_speed: cruiseSpeed,
                    departure_time: departureTimeUTC || null
                }),
                credentials: 'include'
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);

            const data = await response.json();
            console.log('Flight plan data:', data);
        } catch (error) {
            console.error('Error fetching flight plan:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div className="text-4xl text-center font-mono font-extralight bg-gradient-to-r from-[#e39292] to-accent bg-[length:250%_100%] bg-clip-text text-transparent drop-shadow-[0_0_30px_rgba(255,107,74,0.5)] animate-[shimmer_5s_ease-in-out_infinite]">
                Comprehensive Flight Search Options
            </div>
            <div className="flex items-center gap-x-16 mx-4 mt-10">
                <div className="flex flex-col">
                    <label htmlFor="departure" className="flex font-geist-outfit justify-center font-medium mb-4 text-gray-300">
                        Departure Airport
                    </label>
                    <input
                        id="departure"
                        ref={departureRef}
                        autoFocus
                        disabled={loading}
                        type="text"
                        value={departureAirport}
                        onChange={(e) => setDepartureAirport(e.target.value)}
                        placeholder="Enter ICAO Code"
                        maxLength={4}
                        className="w-44 p-2 bg-secondary/65 rounded-lg font-geist-sans text-[15px] focus:text-left text-center text-white
                    placeholder:text-white/50 placeholder:text-[14px] placeholder:text-left placeholder:font-outfit border border-transparent
                    focus:border-white/20 focus:border-[0.5px] outline-none transition-all duration-300 ease-in"
                    />
                </div>
                <div className="flex flex-col">
                    <label htmlFor="destination" className="flex font-geist-outfit justify-center font-medium mb-4 text-gray-300">
                        Arrival Airport
                    </label>
                    <input
                        id="arrival"
                        ref={arrivalRef}
                        autoFocus
                        disabled={loading}
                        type="text"
                        value={arrivalAirport}
                        onChange={(e) => setArrivalAirport(e.target.value)}
                        placeholder="Enter ICAO Code"
                        maxLength={4}
                        className={cn(
                            `w-44 p-2 bg-secondary/65 rounded-lg font-geist-sans text-[15px] focus:text-left text-center text-white
                                placeholder:text-white/50 placeholder:text-[14px] placeholder:text-left placeholder:font-outfit border border-transparent
                                focus:border-white/20 focus:border-[0.5px] outline-none transition-all duration-300 ease-in`
                        )}
                    />
                </div>
                <div className="flex flex-col">
                    <label htmlFor="waypoints" className="flex font-geist-outfit justify-center font-medium mb-4 text-gray-300">
                        Waypoints
                    </label>
                    <input
                        id="waypoints"
                        ref={waypointsRef}
                        autoFocus
                        disabled={loading}
                        type="text"
                        value={waypoints.join(", ")}
                        onChange={(e) => handleWaypointsChange(e)}
                        placeholder="(e.g., KORD, KDEN)"
                        maxLength={50}
                        className={cn(
                            `w-44 p-2 bg-secondary/65 rounded-lg font-geist-sans text-[15px] focus:text-left text-center text-white
                                placeholder:text-white/50 placeholder:text-[14px] placeholder:text-left placeholder:font-outfit border border-transparent
                                focus:border-white/20 focus:border-[0.5px] outline-none transition-all duration-300 ease-in`
                        )}
                    />
                </div>
                <div className="flex flex-col">
                    <label htmlFor="cruise-speed" className="flex font-geist-outfit justify-center font-medium mb-4 text-gray-300">
                        Cruise Speed (knots)
                    </label>
                    <input
                        id="cruise-speed"
                        ref={cruiseSpeedRef}
                        type="number"
                        min={100}
                        max={900}
                        step={1}
                        value={cruiseSpeed !== null && cruiseSpeed !== undefined ? cruiseSpeed : ''}
                        onChange={(e) => {
                            const rawValue = e.target.value;
                            if (rawValue === '') {
                                setCruiseSpeed('');
                                return;
                            }

                            const numValue = Number(rawValue);
                            if (!isNaN(numValue)) {
                                setCruiseSpeed(numValue);
                            }
                        }}
                        onBlur={() => {
                            if (cruiseSpeed === '' || cruiseSpeed === undefined) {
                                setCruiseSpeed(450);
                            } else {
                                setCruiseSpeed(Math.max(100, Math.min(900, cruiseSpeed)));
                            }
                        }}
                        placeholder="Enter Cruise Speed"
                        className={cn(
                            `w-44 p-2 bg-secondary/65 rounded-lg font-geist-sans text-[15px] focus:text-left text-center text-white
     placeholder:text-white/50 placeholder:text-[14px] placeholder:text-left placeholder:font-outfit border border-transparent
     focus:border-white/20 focus:border-[0.5px] outline-none transition-all duration-300 ease-in`
                        )}
                    />
                </div>
                <div className="flex flex-col">
                    <label htmlFor="departure-time" className="flex font-geist-outfit justify-center font-medium mb-4 text-gray-300">
                        Departure Time (UTC)
                    </label>
                    <input
                        type="datetime-local"
                        id="departure-time"
                        value={departureTimeUTC ? departureTimeUTC.slice(0, 16) : new Date().toISOString().slice(0, 16)} // Use state or default
                        onChange={(e) => {
                            const utcTime = new Date(e.target.value).toISOString();
                            setDepartureTimeUTC(utcTime);
                        }}
                        className={cn(
                            `w-46 p-2 bg-secondary/65 rounded-lg font-geist-sans text-[15px] focus:text-left text-center text-white
                                    placeholder:text-white/50 placeholder:text-[14px] placeholder:text-left placeholder:font-outfit border border-transparent
                                    focus:border-white/20 focus:border-[0.5px] outline-none transition-all duration-300 ease-in`
                        )}
                    />
                </div>
                <div className="flex items-center justify-center">
                    <button
                        onSubmit={handleSubmit}
                        id="analyze-btn"
                        className="bg-green-600/70 flex items-center cursor-pointer justify-center rounded-md p-3 text-white"
                    >
                        Analyze Weather
                    </button>
                </div>
            </div>
        </>
    )
}

export default FlightSearchOptions;
