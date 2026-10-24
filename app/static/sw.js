const CACHE="civica-pwa-v2";
const SHELL=["./","./app.css","./app.js","./icon.svg","./manifest.webmanifest"];
self.addEventListener("install",event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener("activate",event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener("fetch",event=>{
  const request=event.request;
  if(request.method!=="GET"||new URL(request.url).origin!==self.location.origin)return;
  event.respondWith(fetch(request).then(response=>{
    if(response.ok&&response.type!=="opaque"){
      const clone=response.clone();
      event.waitUntil(caches.open(CACHE).then(c=>c.put(request,clone)));
    }
    return response;
  }).catch(async()=> (await caches.match(request))||
    (request.mode==="navigate"?(await caches.match("./")):Response.error())));
});
