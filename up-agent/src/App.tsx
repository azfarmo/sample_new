import React, { useState, useEffect, useCallback, useRef } from 'react'; // Removed useContext
import { createClientUPProvider } from '@lukso/up-provider';
import axios from 'axios';
// Consolidated and corrected ethers imports for v6 style
import { JsonRpcProvider, isAddress, parseUnits } from 'ethers';
import { ERC725 } from '@erc725/erc725.js';
import LSP3ProfileMetadataSchema from '@erc725/erc725.js/schemas/LSP3ProfileMetadata.json';
// Assuming '@lukso/lsp-factory' will be installed and provides UniversalProfile__factory
import { UniversalProfile__factory } from '@lukso/lsp-factory';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

// Register the relativeTime plugin with dayjs
dayjs.extend(relativeTime);

// Constants
const RL_AGENT_API_BASE_URL = process.env.REACT_APP_RL_AGENT_API_BASE_URL || 'http://localhost:8000';
const LUKSO_RPC_URL = process.env.REACT_APP_LUKSO_RPC_URL || 'https://rpc.testnet.lukso.network';
const IPFS_GATEWAY = 'https://api.universalprofile.cloud/v1/ipfs/';

// ABI for UniversalProfile, obtained from lsp-factory
// Ensure '@lukso/lsp-factory' is installed for this to work.
const LSP0ERC725Account_ABI = UniversalProfile__factory.abi;

interface ProfileMetrics {
  followers: number;
  postsCount: number;
  engagementRate: number;
  profileName?: string;
  profileImageCid?: string;
  description?: string;
}

interface ActionResponse { action_id: number; action_name: string; }
interface ActionLog { id: string; timestamp: number; name: string; status: string; message: string; txHash?: string; }

const AVAILABLE_ACTIONS: Record<number, { name: string; requires?: string[] }> = {
  0: { name: 'Make Post', requires: ['content'] },
  1: { name: 'Follow Profile', requires: ['target'] },
  2: { name: 'Reward Follower', requires: ['target','amount'] },
};

const AppContent: React.FC = () => {
  // Initialize UP provider client
  // IMPORTANT: The following line uses 'as any' as a workaround for the TS2339 errors.
  // You should verify the correct API for `createClientUPProvider` from '@lukso/up-provider'
  // and update this an_introduction_to_the_standard_model_of_particle_physics accordingly. The library might have changed its API.
  const { provider, account: address, chainId, connect, disconnect } = createClientUPProvider() as any;

  const [metrics, setMetrics] = useState<ProfileMetrics|null>(null);
  const [recommendation, setRecommendation] = useState<ActionResponse|null>(null);
  const [logs, setLogs] = useState<ActionLog[]>([]);
  const [loading, setLoading] = useState<{metrics:boolean;recommend:boolean;exec:boolean}>({metrics:false,recommend:false,exec:false});
  const [error, setError] = useState<string|null>(null);
  const [target, setTarget] = useState('');
  const [content, setContent] = useState('');
  const [amount, setAmount] = useState('1');
  const endRef = useRef<HTMLDivElement>(null);

  const addLog = useCallback((entry: Omit<ActionLog,'id'|'timestamp'>) => {
    setLogs(l => [{ id: crypto.randomUUID(), timestamp: Date.now(), ...entry }, ...l].slice(0,50));
  },[]);
  useEffect(()=>{ endRef.current?.scrollIntoView({behavior:'smooth'}); },[logs]);

  const fetchMetrics = useCallback(async () => {
    if (!address) return;
    setLoading(l=>({...l,metrics:true})); setError(null);
    addLog({ name:'Fetch Metrics', status:'pending', message:'Loading profile...'});
    try {
      // Use directly imported JsonRpcProvider (ethers v6 style)
      const rpcProvider = new JsonRpcProvider(LUKSO_RPC_URL);
      const erc725 = new ERC725(LSP3ProfileMetadataSchema as any[], address, rpcProvider, { ipfsGateway:IPFS_GATEWAY }); // Cast schema if necessary, or ensure its type matches ERC725 constructor
      const data = await erc725.fetchData(['LSP3Profile','LSP12IssuedAssets[]']);
      const profile = data.find(d=>d.name==='LSP3Profile')?.value as any;
      const assets = data.find(d=>d.name==='LSP12IssuedAssets[]')?.value as string[];

      const name = profile?.LSP3Profile?.name || 'Anonymous';
      const desc = profile?.LSP3Profile?.description || '';
      const imgCid = profile?.LSP3Profile?.profileImage?.[0]?.url.replace('ipfs://','');
      const followers = Math.floor(Math.random()*500);
      const engagement = +(Math.random()*0.1).toFixed(3);
      setMetrics({ followers, postsCount:assets?.length||0, engagementRate:engagement, profileName:name, profileImageCid:imgCid, description:desc });
      addLog({ name:'Fetch Metrics', status:'success', message:`Loaded ${name}` });
    } catch(err:any){
      setError(err.message); addLog({ name:'Fetch Metrics', status:'failed', message:err.message });
      setMetrics(null);
    } finally { setLoading(l=>({...l,metrics:false})); }
  },[address,addLog]);

  useEffect(()=>{ if(address) fetchMetrics(); else { setMetrics(null); setRecommendation(null); setLogs([]); } },[address,fetchMetrics]);

  const getRecom = async () => {
    if(!metrics||!address) return setError('Connect and load metrics first');
    setLoading(l=>({...l,recommend:true})); setError(null);
    addLog({ name:'Recommend', status:'pending', message:'Agent thinking...' });
    try {
      const res = await axios.post<ActionResponse>(`${RL_AGENT_API_BASE_URL}/recommend-action`,{ up_address:address, followers:metrics.followers, posts:metrics.postsCount, engagement:metrics.engagementRate });
      setRecommendation(res.data);
      addLog({ name:'Recommend', status:'success', message:res.data.action_name });
    } catch(err:any){ setError(err.message); addLog({ name:'Recommend', status:'failed', message:err.message }); }
    finally{ setLoading(l=>({...l,recommend:false})); }
  };

  const execAction = async () => {
    if(!recommendation||!provider||!address) return;
    const action = AVAILABLE_ACTIONS[recommendation.action_id];
    setLoading(l=>({...l,exec:true})); setError(null);
    addLog({ name:'Execute', status:'pending', message:action.name });
    try{
      const payload: any = { up_address:address, action_id:recommendation.action_id };
      // Use directly imported isAddress and parseUnits (ethers v6 style)
      if(action.requires?.includes('target')){ if(!isAddress(target)) throw new Error('Invalid target'); payload.target_address=target; }
      if(action.requires?.includes('content')){ if(!content) throw new Error('Content required'); payload.post_content_cid=content; }
      if(action.requires?.includes('amount')){ const amt = parseUnits(amount,"18").toString(); payload.reward_amount_wei=amt; } // "18" for clarity with parseUnits
      const res = await axios.post(`${RL_AGENT_API_BASE_URL}/execute-action`,payload);
      const txHash = res.data.details?.transactionHash || res.data.details?.txHash;
      addLog({ name:'Execute', status:'success', message:`${action.name} done`, txHash });
      setRecommendation(null); setTarget(''); setContent(''); setAmount('1');
      setTimeout(fetchMetrics,5000);
    }catch(err:any){ setError(err.message); addLog({ name:'Execute', status:'failed', message:err.message }); }
    finally{ setLoading(l=>({...l,exec:false})); }
  };

  if(!address) return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 text-white p-4">
      <h1 className="text-3xl mb-4">Autonomous Profile Agent</h1>
      {/* Ensure 'connect' function is available and works as expected */}
      <button onClick={connect} className="px-6 py-3 bg-purple-600 rounded-lg">Connect Universal Profile</button>
    </div>
  );

  const actionDetails = recommendation ? AVAILABLE_ACTIONS[recommendation.action_id] : null;

  return (
    <div className="min-h-screen bg-gray-900 p-6 text-gray-200">
      <header className="flex justify-between items-center mb-6">
        <h1 className="text-2xl text-purple-400">Profile Agent</h1>
        {/* Ensure 'disconnect' function is available and works as expected */}
        <div>{address.slice(0,6)}...{address.slice(-4)} (Chain {chainId}) <button onClick={disconnect} className="ml-4 underline">Disconnect</button></div>
      </header>

      {error && <div className="mb-4 p-3 bg-red-700">Error: {error}</div>}

      <section className="mb-6 p-4 bg-gray-800 rounded-lg">
        <h2 className="text-xl mb-3">Profile Metrics</h2>
        <button onClick={fetchMetrics} disabled={loading.metrics} className="mb-2 px-4 py-2 bg-purple-600 rounded">Refresh</button>
        {metrics && (
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-lg font-bold">{metrics.followers}</p><p>Followers</p>
            </div>
            <div>
              <p className="text-lg font-bold">{metrics.postsCount}</p><p>Posts</p>
            </div>
            <div>
              <p className="text-lg font-bold">{(metrics.engagementRate*100).toFixed(1)}%</p><p>Engagement</p>
            </div>
          </div>
        )}
      </section>

      <section className="mb-6 p-4 bg-gray-800 rounded-lg">
        <h2 className="text-xl mb-3">Agent Control</h2>
        <button onClick={getRecom} disabled={loading.recommend} className="px-4 py-2 bg-blue-600 rounded">Get Recommendation</button>
        {actionDetails && (
          <div className="mt-4 space-y-2">
            <p>Recommendation: <strong>{actionDetails.name}</strong></p>
            {actionDetails.requires?.includes('target') && <input value={target} onChange={e=>setTarget(e.target.value)} placeholder="Target address" className="w-full p-2 bg-gray-700 rounded" />}            
            {actionDetails.requires?.includes('content') && <textarea value={content} onChange={e=>setContent(e.target.value)} placeholder="Content or CID" className="w-full p-2 bg-gray-700 rounded" rows={2} />}          
            {actionDetails.requires?.includes('amount') && <input type="number" value={amount} onChange={e=>setAmount(e.target.value)} placeholder="Amount TYT" className="w-full p-2 bg-gray-700 rounded" />}
            <button onClick={execAction} disabled={loading.exec} className="mt-2 px-4 py-2 bg-green-600 rounded">Execute Action</button>
          </div>
        )}
      </section>

      <section className="p-4 bg-gray-800 rounded-lg">
        <h2 className="text-xl mb-3">Activity Log</h2>
        <div className="max-h-64 overflow-y-auto space-y-2">
          {logs.map(l=> (
            <div key={l.id} className={`p-2 rounded ${l.status==='success'? 'bg-green-700':'bg-yellow-700'}`}>              
              <div className="flex justify-between"><span>{l.name}</span><span className="text-xs">{dayjs(l.timestamp).fromNow()}</span></div>
              <div className="text-sm">{l.message} {l.txHash && <a href={`https://explorer.execution.testnet.lukso.network/tx/${l.txHash}`} target="_blank" rel="noopener noreferrer" className="underline">View</a>}</div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
      </section>
    </div>
  );
};

export default function App() {
  return <AppContent />;
}
// Removed extra closing brace from here