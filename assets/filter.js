/* 事業所一覧の絞り込み。
   選択肢と件数はビルド時にHTMLに入っている。ここでは各カードの data-* 属性と
   照らして表示・非表示を切り替えるだけ。JSが動かなければバーは出ず、全件が見える。 */
(function () {
  var bar = document.getElementById("flt");
  if (!bar) return;
  var cards = [].slice.call(document.querySelectorAll(".bizlist .card"));
  var sels = [].slice.call(bar.querySelectorAll("select[data-f]"));
  var out = document.getElementById("flt-n");
  var reset = document.getElementById("flt-reset");
  var empty = document.getElementById("flt-empty");
  var dnote = document.getElementById("flt-daynote");
  var top = document.getElementById("flt-top");
  var hdr = document.querySelector("header");

  // ヘッダーが上に貼りついているので、その下にバーを止める
  function place() {
    var h = hdr ? hdr.offsetHeight : 0;
    bar.style.top = h + "px";
    if (top) top.style.scrollMarginTop = h + 8 + "px";
  }

  function apply(ev) {
    var want = {}, any = false;
    sels.forEach(function (s) {
      if (s.value) { want[s.getAttribute("data-f")] = s.value; any = true; }
    });
    var n = 0;
    cards.forEach(function (c) {
      var ok = true;
      for (var f in want) {
        var v = (c.getAttribute("data-" + f) || "").split("|");
        if (v.indexOf(want[f]) < 0) { ok = false; break; }
      }
      c.hidden = !ok;
      if (ok) n++;
    });
    out.textContent = n;
    reset.hidden = !any;
    if (empty) empty.hidden = n > 0;
    if (dnote) dnote.hidden = !want.day;
    // 地図（map.js）にも絞り込み結果を伝える
    document.dispatchEvent(new CustomEvent("kt:filter"));
    if (ev) {
      // 一覧の途中で条件を変えると、上にあったカードが消えて位置を見失う。先頭に戻す。
      if (top && top.getBoundingClientRect().top < 0) top.scrollIntoView({ block: "start" });
      if (typeof gtag === "function") {
        var t = ev.target, f = t.getAttribute("data-f") || "reset";
        gtag("event", "filter_use", { facet: f, value: t.value || "(all)", results: n });
      }
    }
  }

  sels.forEach(function (s) { s.addEventListener("change", apply); });
  reset.addEventListener("click", function (ev) {
    sels.forEach(function (s) { s.value = ""; });
    apply(ev);
  });
  bar.hidden = false;
  place();
  window.addEventListener("resize", place);
  apply(); // 戻るボタンで選択状態が復元された場合にも合わせる
})();
