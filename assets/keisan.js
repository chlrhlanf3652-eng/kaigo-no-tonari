/* 介護保険の自己負担計算（東京23区・1級地）。
   単位数・単価はすべて制度ガイドと同じ出典（告示第19号・第93号、令和6年度改定）。
   計算：サービスごとに 総額=floor(単位×単価)、保険分=floor(総額×(1-負担割合))、自己負担=総額-保険分。
   区分支給限度基準額を超えたぶんは全額自己負担。どのサービスを枠外にするかは実際にはケアマネジャーが
   決めるが、ここでは各サービスから同じ割合で超えたものとして計算する。 */
(function () {
  var root = document.getElementById("ks");
  if (!root) return;
  var LIMIT = { 1: 16765, 2: 19705, 3: 27048, 4: 30938, 5: 36217 };
  var DAY = { // 通常規模型通所介護 [要介護1..5]
    "3": [370, 423, 479, 533, 588], "4": [388, 444, 502, 560, 617], "5": [570, 673, 777, 880, 984],
    "6": [584, 689, 796, 901, 1008], "7": [658, 777, 900, 1023, 1148], "8": [669, 791, 915, 1041, 1168]
  };
  var SHORT = { tasho: [603, 672, 745, 815, 884], unit: [704, 772, 847, 918, 987] }; // 併設型
  var HOTEL = { tasho: 1545 + 915, unit: 1545 + 2066 }; // 基準費用額：食費＋滞在費（1日）
  function v(id) { var e = document.getElementById(id); return e ? Number(e.value) || 0 : 0; }
  function yen(n) { return Math.round(n).toLocaleString("ja-JP") + "円"; }

  function calc() {
    var lv = v("ks-lv"), rate = v("ks-rate") / 10;
    var svc = [];
    // [名前, 単位/月, 1単位の単価（銭）]
    svc.push(["訪問介護", v("ks-h1") * 244 + v("ks-h2") * 387 + v("ks-h3") * 567 + v("ks-s1") * 179 + v("ks-s2") * 220, 1140]);
    svc.push(["訪問看護", v("ks-k1") * 471 + v("ks-k2") * 823, 1140]);
    var dt = document.getElementById("ks-dt").value;
    svc.push(["デイサービス", v("ks-dn") * (DAY[dt][lv - 1] + (document.getElementById("ks-bath").checked ? 40 : 0)), 1090]);
    var room = document.getElementById("ks-room").value, sd = v("ks-sd");
    svc.push(["ショートステイ", sd * SHORT[room][lv - 1], 1110]);

    var total = svc.reduce(function (a, s) { return a + s[1]; }, 0);
    var limit = LIMIT[lv], ratio = total > limit ? limit / total : 1;
    var inPay = 0, overPay = 0, rows = "";
    svc.forEach(function (s) {
      if (!s[1]) return;
      var inU = Math.floor(s[1] * ratio), overU = s[1] - inU;
      var gross = Math.floor(inU * s[2] / 100); // 単価は銭単位の整数で持つ（小数の誤差を避ける）
      var pay = gross - Math.floor(gross * (10 - v("ks-rate")) / 10);
      var over = Math.floor(overU * s[2] / 100);
      inPay += pay; overPay += over;
      rows += "<tr><th>" + s[0] + "</th><td class=\"num\">" + s[1].toLocaleString("ja-JP") + "単位</td><td class=\"num\">" + yen(pay + over) + "</td></tr>";
    });
    var hotel = sd * HOTEL[room];
    var out = document.getElementById("ks-out");
    if (!total) { out.innerHTML = "<p>使う回数を入れると、ここに1か月の目安が出ます。</p>"; return; }
    var pct = Math.round(total / limit * 100);
    out.innerHTML =
      "<p class=\"ks-big\">1か月の自己負担の目安 <b>" + yen(inPay + overPay + hotel) + "</b></p>" +
      "<div class=\"tw\"><table><thead><tr><th>サービス</th><th>単位数</th><th>自己負担</th></tr></thead><tbody>" + rows +
      (hotel ? "<tr><th>ショートステイの食費・滞在費<br><span class=\"tiny\">保険外・国の基準費用額で計算</span></th><td class=\"num\">—</td><td class=\"num\">" + yen(hotel) + "</td></tr>" : "") +
      "</tbody></table></div>" +
      "<p>1か月の上限（要介護" + lv + "は" + limit.toLocaleString("ja-JP") + "単位）のうち <b>" + pct + "％</b> を使う計算です。" +
      (total > limit ? "<strong>上限を" + (total - limit).toLocaleString("ja-JP") + "単位超えています。</strong>超えた分は全額自己負担になり、上の金額のうち約" + yen(overPay) + "がそれにあたります。" : "上限の範囲内です。") + "</p>";
    if (typeof gtag === "function") gtag("event", "calc_use", { level: lv, over: total > limit ? 1 : 0 });
  }
  root.addEventListener("input", calc);
  root.addEventListener("change", calc);
  calc();
})();
