import {afterEach,beforeEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {JourneyProvider,useJourney} from '../lib/journey-context';
import {Recommendations} from '../components/recommendations';
import {StationDetails} from '../components/station-details';
import {apiGet,statusOf,priceOf,metadataSchema} from '../lib/api';
import fixture from './journey.json';
function Controls(){const j=useJourney();return <><button onClick={()=>void j.search()}>Search</button><span>{j.loading?'Loading':'Ready'}</span>{j.error&&<p role="alert">{j.error}</p>}<Recommendations/><StationDetails/></>}
function mount(){return render(<JourneyProvider><Controls/></JourneyProvider>)}
let detailRequests:string[];
beforeEach(()=>{const storage=new Map<string,string>();vi.stubGlobal('localStorage',{getItem:(key:string)=>storage.get(key)??null,setItem:(key:string,value:string)=>storage.set(key,String(value)),removeItem:(key:string)=>storage.delete(key),clear:()=>storage.clear()});localStorage.clear();detailRequests=[];vi.stubGlobal('fetch',vi.fn(async(input:string)=>{const url=String(input);if(url.includes('metadata'))return new Response(JSON.stringify({connector_types:['CCS'],sort_options:['recommended','fastest']}));if(url.includes('health'))return new Response(JSON.stringify({status:'healthy'}));if(url.includes('chargers/')){detailRequests.push(url);return new Response(JSON.stringify(fixture.recommended_stations[0]));}return new Response(JSON.stringify(fixture));}));});
afterEach(()=>{cleanup();vi.unstubAllGlobals()});
describe('journey dashboard',()=>{
 it('keeps unknown status and missing tariffs neutral',()=>{expect(statusOf(fixture.recommended_stations[0] as never)).toBe('unknown');expect(priceOf(fixture.recommended_stations[0] as never)).toBe('Unavailable')});
 it('shows an initial empty state without invented stations',()=>{mount();expect(screen.getByText('Find a stop that fits your journey')).toBeTruthy();expect(screen.queryByText('Test station')).toBeNull()});
 it('selects a recommendation and requests canonical detail',async()=>{mount();fireEvent.click(screen.getByText('Search'));await screen.findByText('1. Test station');fireEvent.click(screen.getByText('1. Test station'));await waitFor(()=>expect(detailRequests.length).toBeGreaterThan(0));expect(detailRequests[0]).toContain('chargers/ocm%3A123');expect(await screen.findByText('Status unknown')).toBeTruthy();expect(screen.getByText('Verified tariff unavailable')).toBeTruthy()});
 it('shows loading and a real no-match state',async()=>{let resolve!:(r:Response)=>void;vi.mocked(fetch).mockImplementation(async(input)=>String(input).includes('recommendations')?await new Promise<Response>(r=>{resolve=r}):new Response(JSON.stringify(String(input).includes('metadata')?{connector_types:['CCS'],sort_options:['recommended']}:{status:'healthy'})));mount();fireEvent.click(screen.getByText('Search'));expect(screen.getByText('Loading')).toBeTruthy();resolve(new Response(JSON.stringify({...fixture,recommended_stations:[],summary:{stations_found:0,stations_matching_filters:0,best_station_id:null}})));expect(await screen.findByText('No matching charging stops')).toBeTruthy()});
 it('handles missing-provider errors without replacing prior results',async()=>{mount();fireEvent.click(screen.getByText('Search'));await screen.findByText('1. Test station');vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({detail:'Provider not configured'}),{status:503}));fireEvent.click(screen.getByText('Search'));expect(await screen.findByRole('alert')).toBeTruthy();expect(screen.getByText('1. Test station')).toBeTruthy()});
 it('rejects malformed API responses',async()=>{vi.mocked(fetch).mockResolvedValue(new Response('{}'));await expect(apiGet('metadata',metadataSchema)).rejects.toThrow('unexpected response')});
});
