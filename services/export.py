"""
Scoresheet Export

Generate PDF scoresheets matching the official AmpeSports format.
Also supports CSV export for data analysis.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

# Try to import reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph,
        Spacer, Image
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


class ScoresheetExporter:
    """
    Generate PDF scoresheets matching the official AmpeSports format.

    Supports:
    - 1v1 Mode scoresheets
    - Team vs Team scoresheets
    - CSV data export
    """

    def __init__(self):
        if HAS_REPORTLAB:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        """Set up custom paragraph styles."""
        if not HAS_REPORTLAB:
            return

        self.styles.add(ParagraphStyle(
            name='Title',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=20,
        ))

        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=10,
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
        ))

    def export_1v1(self, match_data: dict, filepath: str) -> bool:
        """
        Export a 1v1 match scoresheet as PDF.

        Args:
            match_data: Dictionary containing match information
            filepath: Output file path

        Returns:
            True if export successful, False otherwise
        """
        if not HAS_REPORTLAB:
            return False

        try:
            doc = SimpleDocTemplate(
                filepath,
                pagesize=A4,
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=1*cm,
                bottomMargin=1*cm,
            )

            elements = []

            # Title
            elements.append(Paragraph(
                "AmpeSports — Official Scoresheet",
                self.styles['Title']
            ))

            elements.append(Paragraph(
                "1 vs 1 Match",
                self.styles['Subtitle']
            ))

            elements.append(Spacer(1, 0.5*cm))

            # Match info table
            match_info = [
                ["Date:", match_data.get("date", datetime.now().strftime("%Y-%m-%d"))],
                ["Venue:", match_data.get("venue", "Not specified")],
                ["Age Category:", match_data.get("age_category", "Not specified")],
                ["Total Rounds:", str(match_data.get("total_rounds", 5))],
            ]

            info_table = Table(match_info, colWidths=[3*cm, 10*cm])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(info_table)

            elements.append(Spacer(1, 0.5*cm))

            # Players
            elements.append(Paragraph("Players", self.styles['SectionHeader']))

            players_data = [
                ["", "Player 1", "Player 2"],
                ["Name:", match_data.get("player1_name", "Player 1"),
                 match_data.get("player2_name", "Player 2")],
                ["Jersey #:", str(match_data.get("player1_jersey", "-")),
                 str(match_data.get("player2_jersey", "-"))],
            ]

            players_table = Table(players_data, colWidths=[3*cm, 6*cm, 6*cm])
            players_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(players_table)

            elements.append(Spacer(1, 0.5*cm))

            # Round results
            elements.append(Paragraph("Round Results", self.styles['SectionHeader']))

            rounds = match_data.get("rounds", [])
            round_header = ["Round", "P1 AP", "P2 AP", "P1 Opa", "P1 Oshi",
                           "P2 Opa", "P2 Oshi", "Winner"]

            round_data = [round_header]
            for r in rounds:
                round_data.append([
                    str(r.get("number", "-")),
                    str(r.get("p1_ap", 0)),
                    str(r.get("p2_ap", 0)),
                    str(r.get("p1_opa", 0)),
                    str(r.get("p1_oshi", 0)),
                    str(r.get("p2_opa", 0)),
                    str(r.get("p2_oshi", 0)),
                    r.get("winner", "-"),
                ])

            rounds_table = Table(round_data, colWidths=[1.5*cm, 1.5*cm, 1.5*cm,
                                                        1.8*cm, 1.8*cm, 1.8*cm,
                                                        1.8*cm, 2*cm])
            rounds_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(rounds_table)

            elements.append(Spacer(1, 0.5*cm))

            # Final result
            elements.append(Paragraph("Final Result", self.styles['SectionHeader']))

            p1_total = match_data.get("player1_ap", 0)
            p2_total = match_data.get("player2_ap", 0)
            winner = match_data.get("winner", "Unknown")

            final_data = [
                ["Player 1 Total AP:", str(p1_total)],
                ["Player 2 Total AP:", str(p2_total)],
                ["Match Winner:", winner],
            ]

            final_table = Table(final_data, colWidths=[5*cm, 5*cm])
            final_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
                ('FONTSIZE', (1, 2), (1, 2), 14),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(final_table)

            elements.append(Spacer(1, 0.5*cm))

            # Officials
            elements.append(Paragraph("Officials", self.styles['SectionHeader']))

            officials = match_data.get("officials", {})
            officials_data = [
                ["Master Ampfre:", officials.get("master", "_________________")],
                ["Caller Ampfre:", officials.get("caller", "_________________")],
                ["Recorder 1:", officials.get("recorder1", "_________________")],
                ["Recorder 2:", officials.get("recorder2", "_________________")],
                ["Timer:", officials.get("timer", "_________________")],
                ["Counter:", officials.get("counter", "_________________")],
            ]

            officials_table = Table(officials_data, colWidths=[4*cm, 8*cm])
            officials_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            elements.append(officials_table)

            elements.append(Spacer(1, 1*cm))

            # Signatures
            sig_data = [
                ["Master Ampfre Signature:", "_____________________",
                 "Date:", "_______________"],
            ]
            sig_table = Table(sig_data, colWidths=[4*cm, 5*cm, 2*cm, 4*cm])
            elements.append(sig_table)

            # Footer
            elements.append(Spacer(1, 1*cm))
            elements.append(Paragraph(
                "Generated by AmpsMotion — Official AmpeSports Scoring System",
                ParagraphStyle(
                    name='Footer',
                    fontSize=8,
                    alignment=TA_CENTER,
                    textColor=colors.grey,
                )
            ))

            # Build PDF
            doc.build(elements)
            return True

        except Exception as e:
            print(f"PDF export error: {e}")
            return False

    def export_csv(self, match_data: dict, filepath: str) -> bool:
        """
        Export match data as CSV for analysis.

        Args:
            match_data: Dictionary containing match information
            filepath: Output file path

        Returns:
            True if export successful, False otherwise
        """
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow(["AmpeSports Match Data Export"])
                writer.writerow([])

                # Match info
                writer.writerow(["Match Information"])
                writer.writerow(["Date", match_data.get("date", "")])
                writer.writerow(["Mode", match_data.get("mode", "1v1")])
                writer.writerow(["Total Rounds", match_data.get("total_rounds", 5)])
                writer.writerow([])

                # Players
                writer.writerow(["Players"])
                writer.writerow(["Player 1", match_data.get("player1_name", "Player 1")])
                writer.writerow(["Player 2", match_data.get("player2_name", "Player 2")])
                writer.writerow([])

                # Results
                writer.writerow(["Final Results"])
                writer.writerow(["Player 1 AP", match_data.get("player1_ap", 0)])
                writer.writerow(["Player 2 AP", match_data.get("player2_ap", 0)])
                writer.writerow(["Winner", match_data.get("winner", "")])
                writer.writerow([])

                # Bout-by-bout data
                bouts = match_data.get("bouts", [])
                if bouts:
                    writer.writerow(["Bout Details"])
                    writer.writerow(["Round", "Bout", "Result", "Winner", "Time"])
                    for bout in bouts:
                        writer.writerow([
                            bout.get("round", ""),
                            bout.get("bout", ""),
                            bout.get("result", ""),
                            bout.get("winner", ""),
                            bout.get("time", ""),
                        ])

            return True

        except Exception as e:
            print(f"CSV export error: {e}")
            return False


def check_pdf_support() -> bool:
    """Check if PDF export is available."""
    return HAS_REPORTLAB
