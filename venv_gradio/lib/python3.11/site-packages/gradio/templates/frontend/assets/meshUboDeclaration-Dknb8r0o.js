import{j as e}from"./index-m3WRYQPb.js";const o="sceneUboDeclaration",t=`struct Scene {viewProjection : mat4x4<f32>,
#ifdef MULTIVIEW
viewProjectionR : mat4x4<f32>,
#endif 
view : mat4x4<f32>,
projection : mat4x4<f32>,
vEyePosition : vec4<f32>,};
#define SCENE_UBO
var<uniform> scene : Scene;
`;e.IncludesShadersStoreWGSL[o]||(e.IncludesShadersStoreWGSL[o]=t);const r="meshUboDeclaration",n=`struct Mesh {world : mat4x4<f32>,
visibility : f32,};var<uniform> mesh : Mesh;
#define WORLD_UBO
`;e.IncludesShadersStoreWGSL[r]||(e.IncludesShadersStoreWGSL[r]=n);
//# sourceMappingURL=meshUboDeclaration-Dknb8r0o.js.map
