/* 一覧の地図（デイサービス・ショートステイのみ）。
   ボタンを押したときだけ Leaflet と地理院タイルを読み込む（最初の表示を重くしない）。
   ピンは各カードの data-lat / data-lng から作り、絞り込み（filter.js）で隠れたカードは出さない。 */
(function () {
  var btn = document.getElementById("kmap-btn");
  var box = document.getElementById("kmap");
  var note = document.getElementById("kmap-n");
  if (!btn || !box) return;
  var LV = "1.9.4";
  var CDN = "https://unpkg.com/leaflet@" + LV + "/dist/";
  var map = null, layer = null;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function load(cb) {
    if (window.L) return cb();
    var css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = CDN + "leaflet.css";
    document.head.appendChild(css);
    var js = document.createElement("script");
    js.src = CDN + "leaflet.js";
    js.onload = cb;
    js.onerror = function () {
      box.textContent = "地図を読み込めませんでした。通信状況をご確認ください。";
    };
    document.head.appendChild(js);
  }

  function pins() {
    if (!map) return;
    layer.clearLayers();
    var pts = [];
    [].forEach.call(document.querySelectorAll(".bizlist .card"), function (c) {
      if (c.hidden) return;
      var lat = parseFloat(c.getAttribute("data-lat"));
      var lng = parseFloat(c.getAttribute("data-lng"));
      if (!lat || !lng) return;
      var no = c.querySelector("h3 .no");
      var name = c.querySelector("h3").textContent.replace(no ? no.textContent : "", "");
      var tel = c.querySelector("a.tel");
      var html = "<b>" + (no ? esc(no.textContent) + ". " : "") + esc(name) + "</b><br>" +
        (tel ? '<a href="' + tel.getAttribute("href") + '">' + esc(tel.lastChild.textContent) + "</a>　" : "") +
        '<a href="#' + c.id + '">一覧で見る</a>';
      var m = L.circleMarker([lat, lng], { radius: 8, color: "#fff", weight: 2, fillColor: "#14705f", fillOpacity: 1 });
      m.bindPopup(html);
      layer.addLayer(m);
      pts.push([lat, lng]);
    });
    if (pts.length) map.fitBounds(pts, { padding: [24, 24], maxZoom: 16 });
  }

  btn.addEventListener("click", function () {
    var open = box.hidden;
    box.hidden = !open;
    note.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.firstChild.textContent = open ? "地図を閉じる" : "地図で見る";
    if (!open) return;
    if (typeof gtag === "function") gtag("event", "map_open", {});
    load(function () {
      if (!map) {
        map = L.map(box, { scrollWheelZoom: false });
        L.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png", {
          maxZoom: 18,
          attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル</a>'
        }).addTo(map);
        layer = L.layerGroup().addTo(map);
      }
      map.invalidateSize();
      pins();
    });
  });

  document.addEventListener("kt:filter", pins);
  document.addEventListener("click", function (ev) {
    var a = ev.target.closest && ev.target.closest("a.map");
    if (a && typeof gtag === "function") gtag("event", "map_link", {});
  });
  btn.hidden = false;
})();
