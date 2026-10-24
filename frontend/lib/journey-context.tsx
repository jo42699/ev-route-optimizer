'use client';
import {createContext,useContext,useEffect,useRef,useState,useCallback} from 'react';
import {z} from 'zod';
import {apiGet,metadataSchema,responseSchema,stationSchema,routeSchema,statusOf,type Metadata,type Station,type JourneyResponse,type StopRoute} from './api';
export type Filters={connector:string;power:number;detour:number;sort:string;available:boolean;maxPrice:string;favouritesOnly:boolean};
const defaults:Filters={connector:'',power:50,detour:20,sort:'recommended',available:false,maxPrice:'',favouritesOnly:false};
function useJourneyState(){
 const [origin,setOrigin]=useState('Oxford, UK'),[destination,setDestination]=useState('London, UK');
 const [filters,setFilters]=useState<Filters>(defaults),[metadata,setMetadata]=useState<Metadata|null>(null),[health,setHealth]=useState('Connecting to backend');
 const [data,setData]=useState<JourneyResponse|null>(null),[selectedId,setSelectedId]=useState<string|null>(null),[detail,setDetail]=useState<Station|null>(null);
 const [loading,setLoading]=useState(false),[detailLoading,setDetailLoading]=useState(false),[error,setError]=useState(''),[detailError,setDetailError]=useState('');
 const [favourites,setFavourites]=useState<string[]>([]),[dark,setDark]=useState(false),[stop,setStop]=useState<StopRoute|null>(null),[stopName,setStopName]=useState(''),[stopLoading,setStopLoading]=useState(false),[storageReady,setStorageReady]=useState(false);
 const searchAbort=useRef<AbortController|null>(null),detailAbort=useRef<AbortController|null>(null),stopAbort=useRef<AbortController|null>(null);
 useEffect(()=>{try{setFavourites(JSON.parse(localStorage.getItem('chargesmart-favourites')||'[]'));setDark(localStorage.getItem('chargesmart-theme')==='dark');const prefs=JSON.parse(localStorage.getItem('chargesmart-vehicle')||'null');if(prefs)setFilters(f=>({...f,connector:typeof prefs.connector==='string'?prefs.connector:'',power:typeof prefs.power==='number'?prefs.power:50}));}catch{}setStorageReady(true);
 const controller=new AbortController();apiGet('metadata',metadataSchema,controller.signal).then(setMetadata).catch(e=>{if(e.name!=='AbortError')setError(e.message)});
 apiGet('health',z.object({status:z.string()}),controller.signal).then(h=>setHealth(h.status==='healthy'?'Providers configured':'Provider setup needed')).catch(()=>setHealth('Backend offline'));
 return()=>{controller.abort();searchAbort.current?.abort();detailAbort.current?.abort();stopAbort.current?.abort()};},[]);
 useEffect(()=>{document.documentElement.dataset.theme=dark?'dark':'light';if(storageReady)localStorage.setItem('chargesmart-theme',dark?'dark':'light')},[dark,storageReady]);
 useEffect(()=>{if(storageReady)localStorage.setItem('chargesmart-favourites',JSON.stringify(favourites))},[favourites,storageReady]);
 const search=useCallback(async(overrides:Partial<Filters>={})=>{
 const active={...filters,...overrides};setFilters(active);
 if(!origin.trim()||!destination.trim()){setError('Enter both an origin and destination.');return;}
 searchAbort.current?.abort();detailAbort.current?.abort();stopAbort.current?.abort();setDetailLoading(false);setStopLoading(false);const controller=new AbortController();searchAbort.current=controller;setLoading(true);setError('');
 const params=new URLSearchParams({origin:origin.trim(),destination:destination.trim(),min_power_kw:String(active.power),max_detour_minutes:String(active.detour),sort_by:active.sort,limit:'10'});if(active.connector)params.set('connector',active.connector);
 try{const result=await apiGet(`journey/recommendations?${params}`,responseSchema,controller.signal);setData(result);setSelectedId(result.summary.best_station_id);setDetail(null);setStop(null);setStopName('');}
 catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Search failed.');}finally{if(!controller.signal.aborted)setLoading(false)}
 },[origin,destination,filters]);
 useEffect(()=>{detailAbort.current?.abort();setDetail(null);setDetailError('');if(!selectedId||!data){setDetailLoading(false);return;}const controller=new AbortController();detailAbort.current=controller;setDetailLoading(true);
 const params=new URLSearchParams({origin:data.journey.origin,destination:data.journey.destination,connector:data.filters.connector.join(',')});
 apiGet(`chargers/${encodeURIComponent(selectedId)}?${params}`,stationSchema,controller.signal).then(setDetail).catch(e=>{if(!controller.signal.aborted)setDetailError(e.message)}).finally(()=>{if(!controller.signal.aborted)setDetailLoading(false)});return()=>controller.abort();},[selectedId,data]);
 const stations=(data?.recommended_stations||[]).filter(s=>(!filters.available||statusOf(s)==='available')&&(!filters.favouritesOnly||favourites.includes(s.station_id))&&(!filters.maxPrice||(s.data_quality.price_is_verified&&s.pricing.currency=== 'GBP'&&s.pricing.price_per_kwh!==null&&s.pricing.price_per_kwh<=Number(filters.maxPrice))));
 const selected=stations.find(s=>s.station_id===selectedId)||null;
 async function addStop(){if(!selected||!data||stopLoading)return;stopAbort.current?.abort();const controller=new AbortController();stopAbort.current=controller;setStopLoading(true);setDetailError('');try{const params=new URLSearchParams({origin:data.journey.origin,destination:data.journey.destination,via:`${selected.location.latitude},${selected.location.longitude}`});setStop(await apiGet(`journey/route?${params}`,routeSchema,controller.signal));setStopName(selected.name);}catch(e){if(!controller.signal.aborted)setDetailError(e instanceof Error?e.message:'Could not add stop.')}finally{if(!controller.signal.aborted)setStopLoading(false)}}
 const toggleFavourite=(id:string)=>setFavourites(old=>old.includes(id)?old.filter(x=>x!==id):[...old,id]);
 const saveVehicle=(connector:string,power:number)=>{localStorage.setItem('chargesmart-vehicle',JSON.stringify({connector,power}));setFilters(f=>({...f,connector,power}));if(data)void search({connector,power});};
 return {origin,setOrigin,destination,setDestination,filters,setFilters,metadata,health,data,stations,selectedId,setSelectedId,selected: selected ? (detail?.station_id===selected.station_id?{...detail,recommendation:selected.recommendation}:selected):null,loading,detailLoading,error,detailError,search,favourites,toggleFavourite,dark,setDark,stop,stopName,stopLoading,addStop,saveVehicle};
}
const JourneyContext=createContext<ReturnType<typeof useJourneyState>|null>(null);
export function JourneyProvider({children}:{children:React.ReactNode}){const state=useJourneyState();return <JourneyContext.Provider value={state}>{children}</JourneyContext.Provider>}
export function useJourney(){const state=useContext(JourneyContext);if(!state)throw new Error('Missing journey provider');return state;}
