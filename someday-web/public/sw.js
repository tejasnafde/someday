self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  event.waitUntil(
    self.registration.showNotification(data.title || "Someday", {
      body: data.body || "",
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: data.url || "/" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((list) => {
      const url = event.notification.data?.url || "/";
      for (const client of list) {
        if (client.url.endsWith(url) && "focus" in client) return client.focus();
      }
      return clients.openWindow(url);
    })
  );
});
