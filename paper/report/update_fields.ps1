# Open the report in Word, update every field (table of contents, lists of figures and tables, captions, page numbers), save it, export a PDF next to it
# and print the page count. Word must be installed; the file is saved in place. Usage: update_fields.ps1 <path to .docx>
param([string]$Docx)
$ErrorActionPreference = "Stop"
$pdf = [System.IO.Path]::ChangeExtension($Docx, ".pdf")
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $d = $word.Documents.Open($Docx)
  $d.Repaginate()
  $null = $d.Fields.Update()
  foreach ($t in $d.TablesOfContents) { $t.Update() }
  foreach ($t in $d.TablesOfFigures) { $t.Update() }
  $d.Repaginate()
  foreach ($t in $d.TablesOfContents) { $t.UpdatePageNumbers() }
  foreach ($t in $d.TablesOfFigures) { $t.UpdatePageNumbers() }
  $d.Save()
  $d.ExportAsFixedFormat($pdf, 17)
  "pages (Word, whole document): " + $d.ComputeStatistics(2)
  "words: " + $d.ComputeStatistics(0)
  "tables: " + $d.Tables.Count + ", inline pictures: " + $d.InlineShapes.Count + ", sections: " + $d.Sections.Count
  "table of contents entries: " + $d.TablesOfContents.Item(1).Range.Paragraphs.Count
  $d.Close($true)
} finally { $word.Quit() }
