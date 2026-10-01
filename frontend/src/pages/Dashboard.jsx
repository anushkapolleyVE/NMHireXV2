import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { getUserDashboard } from '../utils/api';

export default function Dashboard() {
  const [filterText, setFilterText] = useState('All jobs');
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true);
        const data = await getUserDashboard();
        setDashboardData(data);
      } catch (err) {
        console.error("Error fetching dashboard:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  return (
    <div className="relative min-h-screen w-full overflow-hidden antialiased pb-20">
      <div className="glow-bg-large top-[-30%] left-[-20%] animate-pulse-slow"></div>
      <div
        className="glow-bg-large bottom-[-20%] right-[-10%] animate-pulse-slow"
        style={{ animationDelay: '2s', background: 'radial-gradient(circle, rgba(20,184,166,0.1) 0%, rgba(59,130,246,0.05) 40%, rgba(2,6,23,0) 70%)' }}
      ></div>

      <Header />

      <main className="relative z-10">
        <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-6 animate-slide-up opacity-0-init animate-delay-100">
            <div>
              <div className="mb-2 inline-flex items-center gap-2.5 rounded-full bg-slate-800/80 px-3 py-1.5 ring-1 ring-slate-700">
                <span className="size-2 rounded-full bg-brand shadow-[0_0_10px_rgba(59,130,246,0.8)]"></span>
                <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-300">02 · Recruiter dashboard</p>
              </div>
              <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl mt-2 text-white">
                Good morning, {dashboardData?.user_name || 'Recruiter'}.
              </h1>
              <p className="mt-3 text-base text-slate-400">Here's your hiring pipeline at a glance.</p>
            </div>
            <Link to="/match-agent" className="btn-neon rounded-xl px-5 py-3.5 text-sm font-bold text-white flex items-center gap-2 group">
              Create new match
              <span className="transition-transform group-hover:translate-x-1">→</span>
            </Link>
          </div>

          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 animate-slide-up opacity-0-init animate-delay-200">
            <div className="glass-dark glass-dark-card rounded-2xl p-6 relative overflow-hidden group">
              <div className="absolute right-0 top-0 p-4 opacity-5 text-brand transition-transform duration-500 group-hover:scale-110 group-hover:rotate-12">
                <svg className="w-20 h-20" fill="currentColor" viewBox="0 0 24 24"><path d="M20 6h-4V4c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zM10 4h4v2h-4V4zm10 16H4V8h16v12z" /></svg>
              </div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 relative z-10">Active jobs</p>
              <p className="mt-2 font-display text-5xl font-bold text-white relative z-10">{dashboardData?.metrics?.active_jobs || 0}</p>
              <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-brand/20 px-2 py-1 text-[11px] font-bold text-brand ring-1 ring-brand/30 relative z-10 shadow-[0_0_10px_rgba(59,130,246,0.2)]">
                <span className="size-1.5 rounded-full bg-brand animate-pulse"></span> {dashboardData?.metrics?.active_jobs || 0} searching now
              </p>
            </div>
            <div className="glass-dark glass-dark-card rounded-2xl p-6 relative overflow-hidden group animate-delay-100">
              <div className="absolute right-0 top-0 p-4 opacity-5 text-white transition-transform duration-500 group-hover:scale-110 group-hover:-rotate-12">
                <svg className="w-20 h-20" fill="currentColor" viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z" /></svg>
              </div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 relative z-10">Candidates screened</p>
              <p className="mt-2 font-display text-5xl font-bold text-white relative z-10">{dashboardData?.metrics?.candidates_screened || 0}</p>
              <p className="mt-2 text-[11px] font-semibold text-slate-400 relative z-10">Across active jobs</p>
            </div>
            <div className="glass-dark glass-dark-card rounded-2xl p-6 relative overflow-hidden group animate-delay-200">
              <div className="absolute right-0 top-0 p-4 opacity-5 text-accent transition-transform duration-500 group-hover:scale-110 group-hover:rotate-12">
                <svg className="w-20 h-20" fill="currentColor" viewBox="0 0 24 24"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" /></svg>
              </div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 relative z-10">Strong matches</p>
              <p className="mt-2 font-display text-5xl font-bold text-white relative z-10">{dashboardData?.metrics?.strong_matches || 0}</p>
              <p className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-accent/20 px-2 py-1 text-[11px] font-bold text-accent ring-1 ring-accent/30 relative z-10 shadow-[0_0_10px_rgba(20,184,166,0.2)]">
                <svg className="size-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
                90+ and 80+ matches
              </p>
            </div>
            <div className="glass-dark glass-dark-card rounded-2xl p-6 relative overflow-hidden group animate-delay-300">
              <div className="absolute right-0 top-0 p-4 opacity-5 text-purple-400 transition-transform duration-500 group-hover:scale-110 group-hover:-rotate-12">
                <svg className="w-20 h-20" fill="currentColor" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z" /></svg>
              </div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400 relative z-10">WhatsApp outreach</p>
              <p className="mt-2 font-display text-5xl font-bold text-white relative z-10">{dashboardData?.metrics?.whatsapp_outreach || 0}</p>
              <p className="mt-2 text-[11px] font-semibold text-slate-400 relative z-10">0 interested</p>
            </div>
          </section>

          <div className="mt-6 grid gap-6 lg:grid-cols-12 animate-slide-up opacity-0-init animate-delay-300">
            <section className="glass-dark rounded-[24px] p-6 sm:p-8 lg:col-span-12">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-400">Active jobs</p>
                  <h2 className="mt-1 font-display text-2xl font-bold text-white">Hiring pipeline</h2>
                </div>
                <button
                  onClick={() => setFilterText(filterText === 'All jobs' ? 'Active jobs' : 'All jobs')}
                  className="rounded-xl bg-slate-800/80 px-4 py-2 text-xs font-bold text-slate-300 ring-1 ring-slate-700 hover:bg-slate-700 hover:text-white transition-all"
                >
                  {filterText}
                </button>
              </div>

              <div className="overflow-x-auto pb-2">
                <table className="w-full min-w-[760px] text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-700 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      <th className="pb-4 pl-2">Role</th>
                      <th className="pb-4">Sources</th>
                      <th className="pb-4">Screened</th>
                      <th className="pb-4">Strong</th>
                      <th className="pb-4">Outreach</th>
                      <th className="pb-4 pr-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm">
                    {loading ? (
                      <tr>
                        <td colSpan="6" className="py-8 text-center text-slate-400">
                          <div className="flex justify-center items-center">
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand"></div>
                          </div>
                        </td>
                      </tr>
                    ) : dashboardData?.pipeline?.length > 0 ? dashboardData.pipeline.map((job) => (
                      <tr key={job.job_id} className="table-row-hover border-b border-slate-800 group">
                        <td className="py-4 pl-2 rounded-l-lg">
                          <p className="font-bold text-white">{job.title}</p>
                          <p className="mt-1 text-xs text-slate-400 flex items-center gap-1.5">
                            <span>{job.location}</span> <span className="size-1 rounded-full bg-slate-600"></span> <span>{job.experience}</span>
                          </p>
                        </td>
                        <td className="py-4">
                          <span className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-2 py-1 text-xs font-semibold ring-1 ring-slate-700 text-slate-300">
                            {job.sources}
                          </span>
                        </td>
                        <td className="py-4 font-bold text-white">{job.screened}</td>
                        <td className="py-4 font-bold text-accent">
                          <span className="flex items-center gap-1.5 drop-shadow-[0_0_5px_rgba(20,184,166,0.3)]">
                            <svg className="size-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd"></path></svg>
                            {job.strong}
                          </span>
                        </td>
                        <td className="py-4">
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden ring-1 ring-slate-700">
                              <div className="h-full bg-brand animate-fill-width" style={{ width: job.outreach_total > 0 ? `${(job.outreach_count / job.outreach_total) * 100}%` : '0%' }}></div>
                            </div>
                            <span className="text-xs font-bold text-slate-400">{job.outreach_count} / {job.outreach_total}</span>
                          </div>
                        </td>
                        <td className="py-4 pr-2 text-right rounded-r-lg">
                          <button 
                            onClick={() => navigate('/match-agent', { state: { jobId: job.job_id, autoSearch: true, isScreened: job.screened > 0 || job.status === 'ACTIVE' } })}
                            className="rounded-lg bg-brand px-3 py-1.5 text-xs font-bold text-white hover:shadow-[0_0_15px_rgba(59,130,246,0.4)] transition-all"
                          >
                            View Screened
                          </button>
                        </td>
                      </tr>
                    )) : (
                      <tr><td colSpan="6" className="py-8 text-center text-slate-400">No active pipeline.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            
          </div>

          
        </div>
      </main>
    </div>
  );
}
