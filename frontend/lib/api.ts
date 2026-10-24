import { z } from 'zod';
const nullableNumber = z.number().nullable();
const coord = z.object({latitude:z.number(), longitude:z.number()});
export const stationSchema = z.object({
 station_id:z.string(), name:z.string(), operator:z.string().nullable(), address:z.object({formatted:z.string().nullable()}),location:coord,
 connectors:z.array(z.object({connector_id:z.string().nullable(),type:z.string(),power_kw:nullableNumber,quantity:nullableNumber,total_count:nullableNumber,available_count:nullableNumber,status:z.string().nullable()})),power_kw_max:nullableNumber,
 pricing:z.object({currency:z.string().nullable(),price_per_kwh:nullableNumber,source:z.string().nullable(),last_updated:z.string().nullable()}),
 availability:z.object({status:z.enum(['available','occupied','unavailable','unknown']),available_connectors:nullableNumber,total_connectors:nullableNumber,observed_at:z.string().nullable(),source:z.string().nullable(),is_stale:z.boolean()}),
 route:z.object({detour_minutes:nullableNumber,detour_distance_km:nullableNumber,minutes_from_origin:nullableNumber,method:z.string().nullable()}),
 prediction:z.object({probability_available_on_arrival:z.number().min(0).max(1).nullable(),expected_wait_minutes:nullableNumber,prediction_basis:z.string().nullable(),estimated_arrival_at:z.string().nullable(),generated_at:z.string().nullable(),underlying_observation_at:z.string().nullable(),confidence:nullableNumber,model_version:z.string().nullable()}),
 recommendation:z.object({rank:z.number(),score:z.number(),reasons:z.array(z.string())}).nullable(),amenities:z.array(z.string()).nullable(),access:z.object({is_public:z.boolean().nullable(),opening_hours:z.string().nullable(),access_notes:z.string().nullable()}),
 data_quality:z.object({availability_is_live:z.boolean(),price_is_verified:z.boolean(),last_updated:z.string().nullable(),warnings:z.array(z.string())})
});
export const geometrySchema = z.object({type:z.literal('LineString'),coordinates:z.array(z.tuple([z.number(),z.number()]))});
export const routeSchema = z.object({origin:coord,destination:coord,distance_km:z.number(),duration_minutes:z.number(),distance_label:z.string(),duration_label:z.string(),geometry:geometrySchema,generated_at:z.string()});
export const responseSchema = z.object({journey:z.object({origin:z.string(),destination:z.string(),origin_coordinates:coord,destination_coordinates:coord,distance_label:z.string(),duration_label:z.string(),route_distance_km:z.number(),estimated_driving_duration_minutes:z.number(),route_geometry:geometrySchema,generated_at:z.string()}),filters:z.object({connector:z.array(z.string()),min_power_kw:nullableNumber,max_detour_minutes:z.number(),sort_by:z.string(),limit:z.number()}),summary:z.object({stations_found:z.number(),stations_matching_filters:z.number(),best_station_id:z.string().nullable()}),recommended_stations:z.array(stationSchema),map:z.object({bounds:z.array(z.tuple([z.number(),z.number()])),origin_marker:coord,destination_marker:coord,station_markers:z.array(z.object({station_id:z.string(),location:coord,rank:nullableNumber,availability_status:z.string()}))}),data_quality:z.object({freshness:z.string(),prediction_method:z.string(),warnings:z.array(z.string()),source_availability:z.record(z.string(),z.string())})});
export type Station=z.infer<typeof stationSchema>;
export type JourneyResponse=z.infer<typeof responseSchema>;
export type StopRoute=z.infer<typeof routeSchema>;
export const metadataSchema=z.object({connector_types:z.array(z.string()),sort_options:z.array(z.string())});
export type Metadata=z.infer<typeof metadataSchema>;
export const suggestionsSchema=z.object({suggestions:z.array(z.object({label:z.string(),location:coord}))});
export type Suggestion=z.infer<typeof suggestionsSchema>['suggestions'][number];
export async function apiGet<T>(path:string,schema:z.ZodType<T>,signal?:AbortSignal):Promise<T>{
 const response=await fetch(`/api/backend/${path}`,{signal});
 const body=await response.json();
 if(!response.ok){const messages:Record<number,string>={400:'Check the origin, destination, and filters.',404:'This charging station could not be found.',422:'Check the location and filter values.',502:'A data provider or the backend is temporarily unavailable.',503:'This feature needs backend provider configuration.'};throw new Error(`${messages[response.status] || 'Request failed.'} ${typeof body.detail==='string'?body.detail:''}`);}
 const parsed=schema.safeParse(body);if(!parsed.success)throw new Error('The API returned an unexpected response. Please check frontend/backend versions.');return parsed.data;
}
export function statusOf(s:Station){return s.data_quality.availability_is_live&&!s.availability.is_stale&&s.availability.observed_at!==null&&s.availability.source!==null?s.availability.status:'unknown';}
export function priceOf(s:Station){return s.data_quality.price_is_verified&&s.pricing.price_per_kwh!==null&&s.pricing.currency?`${s.pricing.currency} ${s.pricing.price_per_kwh.toFixed(2)}`:'Unavailable';}
export function timeOf(value:string|null){return value?`${new Date(value).toLocaleString()} (local)`:'Not provided';}
