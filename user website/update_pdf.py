import re
import os

filepath = r"c:\Users\anase\Desktop\user\food_freshness_portal.html"

with open(filepath, "r", encoding="utf-8") as f:
    text = f.read()

new_pdf_func = """      function generatePDF(rec) {
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF({ unit: "mm", format: "a4" });
        const insp = rec.inspection;
        const sensor = rec.sensor || {};
        const ts = insp.Time_Stamp
          ? new Date(insp.Time_Stamp.seconds * 1000)
          : new Date();
        const tsStr = ts.toLocaleString("en-IN", { timeZone: "Asia/Kolkata" });
        const food = insp.food_type || "Unknown";
        const level = insp.Spoilage_Level || "—";
        const device = insp.device_id || "—";
        const user = insp.username || "—";
        const W = 210, M = 20;
        let y = 0;

        // Clean white/light theme header
        doc.setFillColor(248, 250, 252); // slate-50
        doc.rect(0, 0, W, 45, "F");
        
        doc.setDrawColor(99, 102, 241); // indigo-500 line
        doc.setLineWidth(1.5);
        doc.line(0, 45, W, 45);

        doc.setFont("helvetica", "bold");
        doc.setFontSize(9);
        doc.setTextColor(99, 102, 241); // indigo-500
        doc.text("FOOD SPOILAGE DETECTION SYSTEM", M, 18);

        doc.setFontSize(24);
        doc.setTextColor(15, 23, 42); // slate-900
        doc.text("Inspection Report", M, 30);

        doc.setFont("helvetica", "normal");
        doc.setFontSize(8);
        doc.setTextColor(100, 116, 139); // slate-500
        doc.text(`Report ID: ${rec.id}`, M, 38);
        doc.text(`Generated: ${new Date().toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}`, M + 80, 38);

        y = 60;

        // Status badge
        const isFresh = level === "Fresh";
        const isHalf = level === "HalfFresh";
        
        const sc = isFresh ? [16, 185, 129] : isHalf ? [245, 158, 11] : [239, 68, 68];
        const sb = isFresh ? [209, 250, 229] : isHalf ? [254, 243, 199] : [254, 226, 226];
        
        doc.setFillColor(...sb);
        doc.roundedRect(M, y, W - 2 * M, 24, 4, 4, "F");
        doc.setDrawColor(...sc);
        doc.setLineWidth(0.5);
        doc.roundedRect(M, y, W - 2 * M, 24, 4, 4, "S");
        
        doc.setFont("helvetica", "bold");
        doc.setFontSize(14);
        doc.setTextColor(...sc);
        const dlbl = isHalf ? "HALF FRESH" : level.toUpperCase();
        doc.text(`Status: ${dlbl}`, W / 2, y + 15, { align: "center" });
        y += 36;

        // Section: Test Info
        doc.setFont("helvetica", "bold");
        doc.setFontSize(10);
        doc.setTextColor(15, 23, 42);
        doc.text("TEST INFORMATION", M, y);
        doc.setDrawColor(226, 232, 240); // slate-200
        doc.setLineWidth(0.5);
        doc.line(M, y + 3, W - M, y + 3);
        y += 12;

        const infos = [
          ["Food Type", food.toUpperCase()],
          ["Date & Time", tsStr],
          ["Device ID", device],
          ["Inspector", user],
        ];
        
        infos.forEach(([lbl, val], i) => {
          if (i % 2 === 0) {
            doc.setFillColor(248, 250, 252);
            doc.rect(M, y - 5, W - 2 * M, 12, "F");
          }
          const x1 = i % 2 === 0 ? M + 2 : W / 2 + 6;
          const x2 = i % 2 === 0 ? M + 45 : W / 2 + 45;
          
          doc.setFont("helvetica", "bold");
          doc.setFontSize(8);
          doc.setTextColor(100, 116, 139);
          doc.text(lbl, x1, y+2.5);
          
          doc.setFont("helvetica", "normal");
          doc.setFontSize(9);
          doc.setTextColor(15, 23, 42);
          doc.text(String(val), x2, y+2.5);
          
          if (i % 2 === 1) y += 12;
        });
        y += 14;

        // Section: Sensor Readings
        doc.setFont("helvetica", "bold");
        doc.setFontSize(10);
        doc.setTextColor(15, 23, 42);
        doc.text("DETAILED SENSOR ANALYSIS", M, y);
        doc.setDrawColor(226, 232, 240);
        doc.line(M, y + 3, W - M, y + 3);
        y += 12;

        // Table header
        doc.setFillColor(241, 245, 249); // slate-100
        doc.roundedRect(M, y - 6, W - 2 * M, 10, 2, 2, "F");
        const cx = [M + 4, M + 40, M + 80, M + 120, M + 160];
        doc.setFontSize(8);
        doc.setTextColor(71, 85, 105); // slate-600
        ["SENSOR", "MEAN", "MAXIMUM", "STD DEV", "UNIT"].forEach((h, i) => doc.text(h, cx[i], y));
        y += 8;

        SENSORS.forEach((s, i) => {
          if (i % 2 === 0) {
            doc.setFillColor(248, 250, 252);
            doc.rect(M, y - 4, W - 2 * M, 8, "F");
          }
          const mean = sensor[`${s}_mean`] !== undefined ? Number(sensor[`${s}_mean`]).toFixed(3) : "—";
          const max = sensor[`${s}_max`] !== undefined ? Number(sensor[`${s}_max`]).toFixed(3) : "—";
          const std = sensor[`${s}_std`] !== undefined ? Number(sensor[`${s}_std`]).toFixed(3) : "—";
          const unit = s === "Temperature" ? "°C" : s === "Humidity" ? "%RH" : "ppm";
          
          doc.setFont("helvetica", "bold");
          doc.setFontSize(8);
          doc.setTextColor(99, 102, 241); // indigo-500
          doc.text(s, cx[0], y+1);
          
          doc.setFont("helvetica", "normal");
          doc.setTextColor(51, 65, 85); // slate-700
          doc.text(String(mean), cx[1], y+1);
          doc.text(String(max), cx[2], y+1);
          doc.text(String(std), cx[3], y+1);
          doc.setTextColor(100, 116, 139);
          doc.text(unit, cx[4], y+1);
          y += 8;
        });
        y += 10;

        // Recommendation
        doc.setFillColor(...sb);
        doc.roundedRect(M, y, W - 2 * M, 24, 3, 3, "F");
        doc.setFont("helvetica", "bold");
        doc.setFontSize(9);
        doc.setTextColor(...sc);
        doc.text("EXECUTIVE SUMMARY", M + 6, y + 8);
        
        const rtxt = isFresh
            ? "The food sample exhibits baseline sensor values and appears completely fresh. It is safe for consumption and further storage under standard conditions."
            : isHalf
              ? "The sample shows elevated gas readings indicating the onset of spoilage. Use with caution, inspect manually, or consume immediately."
              : "Critical threshold exceeded. The sample is severely spoiled. Do NOT consume. Immediate disposal is recommended to prevent cross-contamination.";
              
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9);
        doc.setTextColor(71, 85, 105); // slate-600
        doc.text(rtxt, M + 6, y + 15, { maxWidth: W - 2 * M - 12, lineHeightFactor: 1.4 });
        
        // Footer
        doc.setDrawColor(226, 232, 240);
        doc.line(M, 280, W - M, 280);
        doc.setFont("helvetica", "italic");
        doc.setFontSize(8);
        doc.setTextColor(148, 163, 184); // slate-400
        doc.text("Food Spoilage Detection System  ·  Official Automated Analysis Report", W / 2, 286, { align: "center" });

        doc.save(`FoodSpoilageReport_${food}_${ts.toLocaleDateString('en-CA').replace(/\//g, '-')}.pdf`);
      }"""

pattern = re.compile(r"      function generatePDF\(rec\) \{.*?\n      \}", re.DOTALL)
new_content = pattern.sub(new_pdf_func, text)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)

print("PDF code updated")
