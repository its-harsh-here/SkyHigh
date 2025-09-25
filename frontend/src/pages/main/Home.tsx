import FlightSearchOptions from "@/components/layouts/main/FlightSearchOptions";

const Home = () => {
    

    return (
        <>
            <main>
                <div className="relative h-screen flex items-start justify-center p-[12vh]">
                    <section className="cardbase">
                        <FlightSearchOptions />
                    </section>
                </div>
            </main>
        </>
    );
}

export default Home;
