import{j as e}from"./index-m3WRYQPb.js";const a="decalFragment",l=`#ifdef DECAL
var decalTempColor=decalColor.rgb;var decalTempAlpha=decalColor.a;
#ifdef GAMMADECAL
decalTempColor=toLinearSpaceVec3(decalColor.rgb);
#endif
#ifdef DECAL_SMOOTHALPHA
decalTempAlpha=decalColor.a*decalColor.a;
#endif
surfaceAlbedo=mix(surfaceAlbedo.rgb,decalTempColor,decalTempAlpha);
#endif
`;e.IncludesShadersStoreWGSL[a]||(e.IncludesShadersStoreWGSL[a]=l);
//# sourceMappingURL=decalFragment-tdzT4eDj.js.map
