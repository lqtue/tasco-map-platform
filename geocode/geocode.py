import os
_D=os.path.dirname(os.path.abspath(__file__))+os.sep
"""Reverse-geocode a coordinate -> current + past Vietnam admin name.
Usage: python3 geocode.py [lat lon]...   (defaults to a demo set)
"""
import sys, geopandas as gpd, pandas as pd, warnings
from shapely.geometry import Point
warnings.filterwarnings("ignore")

CUR=gpd.read_parquet(_D+"data/admin_current.parquet")
PAST=gpd.read_parquet(_D+"data/admin_past.parquet")
XW=pd.read_parquet(_D+"data/crosswalk.parquet")
_=CUR.sindex; _=PAST.sindex

def _hit(df, p):
    c=df.iloc[list(df.sindex.query(p, predicate="intersects"))]
    c=c[c.contains(p)]
    return c

def _cap(s): return s[:1].upper()+s[1:] if s else s

def geocode(lat, lon):
    p=Point(lon, lat); out={"lat":lat, "lon":lon}
    c=_hit(CUR, p)
    if len(c):
        r=c.iloc[0]
        out["current"]=f"{_cap(r.ward_type)} {r.ward_name}, {r.province_type} {r.province_name}"
        out["current_id"]=r.current_id
    pa=_hit(PAST, p)
    if len(pa):
        w=pa[pa.tier=="ward"]; r=(w.iloc[0] if len(w) else pa.iloc[0])
        if r.tier=="ward":
            out["past"]=f"{_cap(r.ward_type)} {r.ward_name}, {r.district_type} {r.district_name}, {r.province_type} {r.province_name}"
        else:
            out["past"]=f"{_cap(r.ward_type)} {r.ward_name}, {r.province_type} {r.province_name} (district tier)"
    if "current_id" in out:
        comp=XW[(XW.current_id.astype(str)==str(out["current_id"]))&(XW.significant==True)]
        names=sorted(set(comp.past_ward.astype(str)))
        if names: out["current_formed_from"]=names
    return out

DEMO=[(21.0278,105.8342,"Hanoi – Ba Đình"),(10.7769,106.7009,"HCMC – District 1"),
      (16.0678,108.2208,"Đà Nẵng"),(20.8449,106.6881,"Hải Phòng centre"),
      (12.2388,109.1967,"Nha Trang"),(10.0452,105.7469,"Cần Thơ"),
      (10.2899,103.9840,"Phú Quốc island"),(8.6833,106.6072,"Côn Đảo island"),
      (16.50,111.60,"Hoàng Sa / Paracels"),(22.3364,103.8438,"Sa Pa highlands")]

pts = [(float(sys.argv[i]),float(sys.argv[i+1]),f"arg{i//2}") for i in range(1,len(sys.argv)-1,2)] or DEMO
for lat,lon,label in pts:
    r=geocode(lat,lon)
    print(f"\n📍 {label}  ({lat}, {lon})")
    print(f"   CURRENT : {r.get('current','— outside mapped area —')}")
    print(f"   PAST    : {r.get('past','— outside mapped area —')}")
    ff=r.get("current_formed_from")
    if ff: print(f"   (current ward merged {len(ff)} former units: {', '.join(ff[:6])}{' …' if len(ff)>6 else ''})")
