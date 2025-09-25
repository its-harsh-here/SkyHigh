import { ReactNode, HTMLAttributes, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion, MotionProps } from 'motion/react';
import { PlaneTakeoffIcon } from 'lucide-react';

type FadeInProps = {
    children: ReactNode;
    delay?: number;
} & MotionProps & HTMLAttributes<HTMLDivElement>;

const FadeIn = ({ children, delay = 0, ...props }: FadeInProps) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.95, filter: 'blur(5px)' }}
        animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
        transition={{ delay, type: 'tween', duration: 0.4, ease: 'easeOut' }}
        {...props}
    >
        {children}
    </motion.div>
);

const UTCTimeSection = () => {
    const [time, setTime] = useState(new Date().toISOString().slice(11, 19));
    useEffect(() => {
        const id = setInterval(() => setTime(new Date().toISOString().slice(11, 19)), 1000);
        return () => clearInterval(id);
    }, []);
    return (
        <div className='backdrop-blur-md rounded-[14px] bg-secondary/45 py-2 px-4 flex items-center text-white hover:text-accent duration-300 transition-colors'>
            <div className="font-mono text cursor-default">
                <FadeIn>
                    {time} UTC
                </FadeIn>
            </div>
        </div>
    );
};

const Navbar = () => {
    return (
        <nav className='fixed w-full py-6 px-20 z-50'>
            <div className="flex items-center justify-between">
                <div className='flex-1 flex'>
                    <FadeIn className="font-geist-mono tracking-wider backdrop-blur-md rounded-[14px]">
                        <Link to="/" className="flex items-center gap-x-4 bg-secondary/45 rounded-[14px] py-2 px-4">
                            <PlaneTakeoffIcon className="text-white/60 hover:text-white duration-300 transition-colors" size={28} />
                            <div className="text-accent font-outfit font-medium text-2xl tracking-tight">Enhanced Aviation Weather Briefing</div>
                        </Link>
                    </FadeIn>
                </div>

                <div className="flex-1 flex justify-end">
                    <UTCTimeSection />
                </div>
            </div>
        </nav>
    )
}

export default Navbar