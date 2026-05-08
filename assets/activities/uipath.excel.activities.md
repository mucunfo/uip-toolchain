# uipath.excel.activities
Assembly: UiPath.Excel.Activities v3.3.0.0
PackageVersion: 3.3.0-preview
ActivityCount: 128

## UiPath.CSV.Activities.AppendCsvFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  // CaminhoDoArquivo
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
- optional:
  - Delimitator : UiPath.CSV.DelimitatorOptions [Plain]  // Delimitador
  - Encoding : String [In]  // Codificação
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CSV.Activities.AppendWriteCsvFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  @group=File  // CaminhoDoArquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // Arquivo
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
- optional:
  - CsvAction : UiPath.CSV.Activities.CsvWriteAction [Plain]  // Como escrever
  - Delimitator : UiPath.CSV.DelimitatorOptions [Plain]  // Delimitador
  - DelimitatorForViewModel : UiPath.CSV.Activities.DelimiterOptions [Plain]  // Delimitador
  - Encoding : String [In]  // Codificação
  - AddHeaders : Boolean [Plain]  // Adicionar Cabeçalhos
  - ShouldQuote : Boolean [Plain]  // DeveEstarEntreAspas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CSV.Activities.CsvWriteAction
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.CSV.Activities.DelimiterOptions
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.CSV.Activities.ReadCsvFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  @group=File  // CaminhoDoArquivo
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // Arquivo
- optional:
  - DataTable : Data.DataTable [Out]  // TabelaDeDados
  - Delimitator : UiPath.CSV.DelimitatorOptions [Plain]  // Delimitador
  - DelimitatorForViewModel : UiPath.CSV.Activities.DelimiterOptions [Plain]  // Delimitador
  - IncludeColumnNames : Boolean [Plain] = true  // Tem cabeçalhos
  - Encoding : String [In]  // Codificação
  - IgnoreQuotes : Boolean [In]  // IgnorarAspas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CSV.Activities.WriteCsvFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  // CaminhoDoArquivo
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
- optional:
  - AddHeaders : Boolean [Plain]  // Adicionar Cabeçalhos
  - ShouldQuote : Boolean [Plain]  // DeveEstarEntreAspas
  - Encoding : String [In]  // Codificação
  - Delimitator : UiPath.CSV.DelimitatorOptions [Plain]  // Delimitador
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.AppendRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.AddSensitivityLabelX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // Pasta de trabalho
  - **SensitivityLabel** : Object [In]  // Rótulo de confidencialidade
- optional:
  - Justification : String [In]  // Justificativa
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.AppendRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceRange** : UiPath.Excel.IReadRangeRef [In]  // Intervalo do Excel a anexar
  - **DestinationRange** : UiPath.Excel.IReadWriteRangeRef [In]  // Acrescentar após intervalo
- optional:
  - PasteOptions : UiPath.Excel.CopyPasteRangeOptions [Plain]  // O que copiar
  - Transpose : Boolean [Plain]  // Transpor
  - HasHeaders : Boolean [Plain]  // Excluir cabeçalhos de origem
  - StartingColumnName : String [In]  // Starting in column
  - DestinationHasHeaders : Boolean [Plain]  // Destino tem cabeçalhos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.AutoFillX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **StartRange** : UiPath.Excel.IWellDefinedReadRangeRef [In]  // Intervalo inicial
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.AutoFitX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // Intervalo
- optional:
  - Columns : Boolean [Plain]  // Colunas
  - Rows : Boolean [Plain]  // Linhas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ChangePivotTableDataSourceX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **PivotTable** : UiPath.Excel.IPivotTableRef [In]  // Tabela dinâmica
  - **NewSourceRange** : UiPath.Excel.IWellDefinedReadRangeRef [In]  // Nova origem
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ChartModifications.ChangeDataRangeModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // Intervalo de dados
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ChartModifications.ModifyChartTitleModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Title : String [In]  // Título
  - ShowTitle : Boolean [Plain] = true  // Mostrar título
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ChartModifications.ShowHideDataLabelsModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ShowDataLabels : Boolean [Plain] = false  // Mostrar rótulos de dados
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ChartModifications.ShowHideLegendModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ShowLegend : Boolean [Plain] = true  // Mostrar legenda
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ChartModifications.UpdateAxisBoundsModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Axis : UiPath.Excel.Activities.Business.ChartModifications.AxisOrientation [Plain] = 0  // Eixo
  - MinBound : Double [In]  // Limite mín.
  - MaxBound : Double [In]  // Limite máx.
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ChartModifications.UpdateAxisTitleModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Axis : UiPath.Excel.Activities.Business.ChartModifications.AxisOrientation [Plain] = 0  // Eixo
  - ShowTitle : Boolean [Plain]  // Mostrar título
  - Title : String [In]  // Título
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ClearRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TargetRange** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo a limpar
- optional:
  - HasHeaders : Boolean [Plain]  // Tem cabeçalhos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.CopyChartToClipboardX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Chart** : UiPath.Excel.IChartRef [In]  // Gráfico
- optional:
  - Action : UiPath.Excel.ExcelChartAction [Plain]  // Ação
  - FilePath : String [In]  // Nome do arquivo
  - ReplaceFile : Boolean [Plain]  // Substituir arquivo existente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.CopyPasteRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceRange** : UiPath.Excel.IReadRangeRef [In]  // Intervalo de origem
  - **DestinationRange** : UiPath.Excel.IReadWriteRangeRef [In]  // Destino
- optional:
  - PasteOptions : UiPath.Excel.CopyPasteRangeOptions [Plain]  // O que copiar
  - ExcludeHeaders : Boolean [Plain] = false  // Excluir cabeçalho do intervalo de origem
  - ExcludeHeaderFromSourceTable : Boolean [Plain] = true  // Excluir cabeçalhos da tabela de origem
  - Transpose : Boolean [Plain]  // Transpor
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.CreatePivotTableX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IWellDefinedReadRangeRef [In]  // Intervalo da tabela
  - **TableName** : String [In]  // Nome da nova tabela
  - **DestinationRange** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo de destino
  - **LayoutRowType** : UiPath.Excel.PivotTableLayoutRowType [Plain]  // Layout
- optional:
  - ValuesMode : UiPath.Excel.PivotTableValuesMode [Plain]  // Values added as
  - HasHeaders : Boolean [Plain]
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.CreatePivotTableXv2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // Intervalo da tabela
  - **TableName** : String [In]  // Nome da nova tabela
  - **DestinationRange** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo de destino
  - **LayoutRowType** : UiPath.Excel.PivotTableLayoutRowType [Plain]  // Layout
- optional:
  - ValuesMode : UiPath.Excel.PivotTableValuesMode [Plain]  // Values added as
  - HasHeaders : Boolean [Plain]
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.CreateTableX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo da tabela
- optional:
  - TableName : String [In]  // Nome da tabela (opcional)
  - HasHeaders : Boolean [Plain]  // Tem cabeçalhos
  - ReplaceExisting : Boolean [Plain] = true  // Substituir existente
  - OutTableName : String [Out]  // Salvar novo nome de tabela como
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.DeleteColumnX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo de origem
  - **ColumnName** : String [In]  // Nome da coluna
- optional:
  - HasHeaders : Boolean [Plain]  // Tem cabeçalhos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.DeleteRowsX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo de origem
  - **DeleteRowsOption** : UiPath.Excel.DeleteRowsOption [Plain]  // O que excluir
- optional:
  - RowPositions : String [In]  // Na posição
  - HasHeaders : Boolean [Plain]  // Tem cabeçalhos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.DeleteSheetX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Sheet** : UiPath.Excel.ISheetRef [In]  // Selecionar planilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.DuplicateSheetX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SheetToDuplicate** : UiPath.Excel.ISheetRef [In]  // Planilha a duplicar
  - **NewSheetName** : String [In]  // Renomear como
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ExcelApplicationCard
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **WorkbookPath** : String [In]  // Caminho da pasta de trabalho
- optional:
  - Password : String [In]  // Senha
  - EditPassword : String [In]  // Editar senha
  - Visible : Boolean [Plain] = true  // Visível
  - CreateNewFile : Boolean [Plain] = true  // Criar se não existir
  - AutoSave : Boolean [Plain] = true  // Salvar alterações
  - ReadOnly : Boolean [Plain] = false  // SomenteLeitura
  - KeepExcelFileOpen : Boolean [Plain] = false  // Manter arquivo Excel aberto
  - TemplatePath : String [In]  // Modelo
  - UseTemplate : Boolean [Plain] = false  // Usar modelo
  - ReadFormatting : Nullable<UiPath.Excel.ReadFormattingOptions> [Plain]  // Ler formatação
  - ResizeWindow : UiPath.Excel.Model.ResizeWindowOptions [Plain]  // Redimensionar janela
  - SensitivityOperation : UiPath.Excel.ExcelLabelOperation [Plain]  // Operação de confidencialidade
  - SensitivityLabel : Object [In]  // Rótulo de confidencialidade
  - Body : Activities.ActivityAction<UiPath.Excel.IWorkbookQuickHandle> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ExcelForEachRow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // No intervalo
  - **HasHeaders** : Boolean [Plain]  // Tem cabeçalhos
- optional:
  - Body : Activities.ActivityAction<UiPath.Excel.CurrentRowQuickHandle,Int32> [Plain]
  - EmptyRowBehavior : UiPath.Excel.EmptyRowBehavior [Plain]  // Comportamento de linha vazia
  - SaveAfterEachRow : Boolean [Plain]  // Salvar depois de cada linha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ExcelForEachRowX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // No intervalo
  - **HasHeaders** : Boolean [Plain]  // Tem cabeçalhos
- optional:
  - Body : Activities.ActivityAction<UiPath.Excel.CurrentRowQuickHandle,Int32> [Plain]
  - EmptyRowBehavior : UiPath.Excel.EmptyRowBehavior [Plain]  // Comportamento de linha vazia
  - SaveAfterEachRow : Boolean [Plain]  // Salvar depois de cada linha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ExcelProcessScopeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Body : Activities.ActivityAction<UiPath.Excel.IExcelProcess> [Plain]
  - ProcessMode : Nullable<UiPath.Excel.ExcelProcessMode> [Plain]  // Modo de processo
  - LaunchMethod : Nullable<UiPath.Excel.ExcelStartMethod> [Plain]  // Método de inicialização
  - LaunchTimeout : Nullable<Int32> [Plain]  // Tempo limite de lançamento
  - FileConflictResolution : Nullable<UiPath.Excel.ExcelFileConflictResolution> [Plain]  // Resolução de conflito de arquivos
  - ExistingProcessAction : Nullable<UiPath.Excel.ExistingExcelProcessAction> [Plain]  // Ação de processos existentes
  - DisplayAlerts : Nullable<Boolean> [Plain]  // Exibir alertas
  - ShowExcelWindow : Nullable<Boolean> [Plain]  // Mostrar janela do Excel
  - MacroSettings : Nullable<UiPath.Excel.MacroSetting> [Plain]  // Configurações de macro
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ExecuteMacroArgumentX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ArgumentValue** : Object [In]  // Valor do argumento
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ExecuteMacroX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // Nome da pasta de trabalho
  - **MacroName** : String [In]  // Nome da macro
- optional:
  - Result : ? [Out]  // Resultado da macro
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ExportExcelToCsvX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FilePath** : String [In]  // CaminhoDoArquivo
  - **TargetRange** : UiPath.Excel.IReadRangeRef [In]  // TabelaDeDados
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.FillRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DestinationRange** : UiPath.Excel.IWellDefinedReadWriteRangeRef [In]  // Onde escrever
  - **Value** : Object [In]  // O que escrever
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.FilterPivotTableX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Table** : UiPath.Excel.IPivotTableRef [In]  // Tabela dinâmica a filtrar
- optional:
  - ColumnName : String [In]  // Nome da coluna
  - FilterArgument : UiPath.Excel.Activities.Business.Filter.FilterArgument [Plain]
  - ClearFilter : Boolean [Plain]  // Limpar filtros existentes
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.FilterX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo de origem
- optional:
  - ColumnName : String [In]  // Nome da coluna
  - FilterArgument : UiPath.Excel.Activities.Business.Filter.FilterArgument [Plain]
  - HasHeaders : Boolean [Plain]
  - ClearFilter : Boolean [Plain]  // Limpar filtros existentes
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.FindFirstLastDataRowX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // Intervalo de origem
  - **ColumnName** : String [In]  // Nome da coluna
  - **LastRowIndex** : Int32 [Out]  // Índice da última linha
- optional:
  - FirstRowOffset : Int32 [Plain]  // Deslocamento da primeira linha
  - LastRowOffset : Int32 [Plain]  // Deslocamento da última linha
  - BlankRowsToSkip : Int32 [Plain]  // Linhas em branco a pular
  - HasHeaders : Boolean [Plain]  // Tem cabeçalhos
  - ConfigureLastRowAs : UiPath.Excel.LastRowConfiguration [Plain]  // Configurar última linha como
  - VisibleRowsOnly : Boolean [Plain]  // Apenas linhas visíveis
  - FirstRowIndex : Int32 [Out]  // Índice da primeira linha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.FindReplaceValueX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Operation** : UiPath.Excel.FindReplaceOptions [Plain]  // Operação
  - **WhereToSearch** : UiPath.Excel.IReadRangeRef [In]  // Onde pesquisar
  - **ValueToFind** : Object [In]  // Valor a encontrar
- optional:
  - ReplaceWith : Object [In]  // Substituir por
  - LookIn : UiPath.Excel.LookInOptions [Plain]  // Procurar em
  - MatchCase : Boolean [Plain] = false  // Diferenciar maiúsculas/minúsculas
  - MatchEntireCellContents : Boolean [Plain] = false  // Coincidir conteúdo inteiro da célula
  - FoundAt : String [Out]  // Localizado em
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ForEachSheetX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // Pasta de trabalho
- optional:
  - Body : Activities.ActivityAction<UiPath.Excel.WorksheetQuickHandle,Int32> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.FormatRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // Intervalo de origem
- optional:
  - Format : UiPath.Excel.Activities.Business.ICellFormat [Plain]
  - Alignment : UiPath.Excel.AlignmentOptions [Plain]
  - Font : UiPath.Excel.FontOptions [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.GetSensitivityLabelX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // Pasta de trabalho
- optional:
  - SensitivityLabel : UiPath.Excel.IExcelLabelObject [Out]  // Rótulo de confidencialidade
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.InsertColumnX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo
  - **RelativeColumnName** : String [In]  // Relativo à coluna
  - **RelativePosition** : UiPath.Excel.ColumnRelativePosition [Plain]  // Onde inserir
- optional:
  - NewColumnName : String [In]  // Adicionar cabeçalho
  - ColumnFormat : UiPath.Excel.Activities.Business.ICellFormat [Plain]  // Formato
  - HasHeaders : Boolean [Plain]  // Tem cabeçalhos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.InsertExcelChartX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // Intervalo de dados
  - **InsertIntoSheet** : UiPath.Excel.ISheetRef [In]  // Inserir na planilha
  - **ChartCategory** : UiPath.Excel.ExcelChartCategory [Plain]  // Categoria do gráfico
  - **ChartType** : UiPath.Excel.ExcelChartType [Plain]  // Tipo de gráfico
  - **ChartHeight** : Int32 [In]  // Altura do gráfico
  - **ChartWidth** : Int32 [In]  // Largura do gráfico
  - **Left** : Int32 [In]  // Gráfico à esquerda
  - **Top** : Int32 [In]  // Gráfico superior
- optional:
  - InsertedChart : UiPath.Excel.IChartRef [Out]  // Salvar gráfico em
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.InsertRowsX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo de origem
  - **NbOfRows** : Int32 [In]  // Número de linhas
- optional:
  - InsertPosition : UiPath.Excel.InsertRowPosition [Plain]  // Inserir posição
  - SpecificIndex : Int32 [In]  // Índice específico
  - HasHeaders : Boolean [Plain]  // Tem cabeçalhos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.InsertSheetX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // Criar na pasta de trabalho
  - **Name** : String [In]  // Nome da nova planilha
- optional:
  - ReferenceNewSheetAs : UiPath.Excel.ISheetRef [Out]  // Referenciar nova planilha como
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.InvokeVBAArgumentX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ArgumentValue** : Object [In]  // Valor do argumento
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.InvokeVBAX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // Pasta de trabalho de destino
  - **EntryMethodName** : String [In]  // Nome do método de entrada
  - **CodeFilePath** : String [In]  // Caminho do arquivo de código
- optional:
  - Result : ? [Out]  // Saída
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.LookupX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceRange** : UiPath.Excel.IReadRangeRef [In]  // Intervalo
  - **Label** : Object [In]  // O valor a ser pesquisado
- optional:
  - ResultRange : UiPath.Excel.IReadRangeRef [In]  // Origem dos resultados
  - Value : ? [Out]  // Resultado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.MatchFunctionX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ValueToMatch** : Object [In]  // Value to match
  - **InRange** : UiPath.Excel.IWellDefinedReadRangeRef [In]  // In range
- optional:
  - MatchFunctionType : UiPath.Excel.MatchType [Plain]  // Match type
  - SaveTo : Int32 [Out]  // Save to
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.PivotTableFieldX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FieldName** : String [In]  // Campo
- optional:
  - Type : UiPath.Excel.Activities.Business.PivotTableFieldType [Plain]  // É um(a)
  - Function : UiPath.Excel.PivotTableFunction [Plain]  // Função
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ProtectSheetX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Sheet** : UiPath.Excel.ISheetRef [In]  // Planilha
- optional:
  - Password : String [In]  // Senha
  - IsPasswordHidden : Boolean [Plain] = false
  - AdditionalPermissions : UiPath.Excel.ProtectSheetAdditionalPermissions [Plain]  // Permissões adicionais
  - SecurePassword : Security.SecureString [In]  // Senha (SecureString)
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ReadCellFormulaX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : UiPath.Excel.IReadCellRef [In]  // Célula
- optional:
  - SaveTo : String [Out]  // Salvar em
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ReadCellValueX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : UiPath.Excel.IReadCellRef [In]  // Célula
- optional:
  - GetFormattedText : Boolean [Plain]  // Obter texto formatado
  - SaveTo : ? [Out]  // Salvar em
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.ReadRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // Intervalo
- optional:
  - ReadFormatting : Nullable<UiPath.Excel.ReadFormattingOptions> [Plain]  // Ler formatação
  - HasHeaders : Boolean [Plain] = true  // Tem cabeçalhos
  - VisibleOnly : Boolean [Plain] = true  // Apenas linhas visíveis
  - SaveTo : Data.DataTable [Out]  // Salvar em
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.RefreshDataConnectionsX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // Pasta de trabalho
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.RefreshPivotTableX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Table** : UiPath.Excel.IPivotTableRef [In]  // Tabela dinâmica a atualizar
  - **LayoutRowType** : Nullable<UiPath.Excel.PivotTableLayoutRowType> [Plain]  // Layout
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.RemoveDuplicatesX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo
- optional:
  - Columns : Collections.Generic.List<Activities.InArgument<String>> [Plain]
  - HasHeaders : Boolean [Plain] = true  // Tem cabeçalhos
  - ColumnsCompareMode : UiPath.Excel.ColumnsCompare [Plain] = 0  // Colunas a serem comparadas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.RenameSheetX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **From** : UiPath.Excel.ISheetRef [In]  // De
  - **To** : String [In]  // Para
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.SaveAsPdfX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // PastaDeTrabalho
  - **DestinationPdfPath** : String [In]  // Caminho do PDF de destino
- optional:
  - StartPage : Nullable<Int32> [In]  // Página inicial
  - EndPage : Nullable<Int32> [In]  // Página final
  - SaveQuality : UiPath.Excel.PdfSaveQuality [Plain]  // Qualidade para salvar
  - ReplaceExisting : Boolean [Plain] = true  // Substituir existente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.SaveExcelFileAsX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // PastaDeTrabalho
  - **SaveAsFileType** : UiPath.Excel.ExcelSaveAsType [Plain]  // Salvar como tipo
  - **FilePath** : String [In]  // Salvar como arquivo
- optional:
  - ReplaceExisting : Boolean [Plain] = true  // Substituir existente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.SaveExcelFileX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // PastaDeTrabalho
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.SequenceX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Variables : Collections.ObjectModel.Collection<Activities.Variable> [Plain]
  - Activities : Collections.ObjectModel.Collection<Activities.Activity> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.SortColumnX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ColumnName** : String [In]
- optional:
  - SortDirection : UiPath.Excel.Activities.Business.SortDirectionType [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.SortX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadWriteRangeRef [In]  // Intervalo
- optional:
  - HasHeaders : Boolean [Plain]
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.TextToColumnsX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceRange** : UiPath.Excel.IWellDefinedReadRangeRef [In]  // Intervalo de origem
  - **DestinationRange** : UiPath.Excel.IReadWriteRangeRef [In]  // Destino
  - **ParsingType** : UiPath.Excel.TextToColumnsParsingType [Plain]  // Tipo de análise
- optional:
  - NumberOfCharactersPerColumn : Int32 [In]  // Número de caracteres por coluna
  - SplitByTabs : Boolean [Plain]  // Dividido por tabulações
  - SplitBySemicolon : Boolean [Plain]  // Dividido por pontos e vírgulas
  - SplitByComma : Boolean [Plain]  // Dividido por vírgulas
  - SplitBySpace : Boolean [Plain]  // Dividido por espaços
  - SplitByLineBreak : Boolean [Plain]  // Split by new line
  - SplitByOther : Boolean [Plain]  // Dividido por outro
  - OtherSeparator : Nullable<Char> [Plain]  // Outro delimitador
  - ConsecutiveOperatorsAsOne : Boolean [Plain]  // Operadores consecutivos como um
  - TextQualifier : UiPath.Excel.TextToColumnsTextQualifier [Plain]  // Qualificador de texto
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.UnprotectSheetX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Sheet** : UiPath.Excel.ISheetRef [In]  // Planilha
- optional:
  - Password : String [In]  // Senha
  - IsPasswordHidden : Boolean [Plain] = false
  - SecurePassword : Security.SecureString [In]  // Senha (SecureString)
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.UpdateChartX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Chart** : UiPath.Excel.IChartRef [In]  // Gráfico
- optional:
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.VLookupX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceRange** : UiPath.Excel.IReadRangeRef [In]  // No intervalo
  - **Label** : Object [In]  // Valor a pesquisar
- optional:
  - ColumnIndex : Int32 [In]  // Índice de coluna
  - ExactMatch : Boolean [Plain]  // Correspondência exata
  - Value : ? [Out]  // Saída em
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.WriteCellX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : UiPath.Excel.IReadWriteCellRef [In]  // Onde escrever
  - **Value** : Object [In]  // O que escrever
- optional:
  - AutoIncrementRow : Boolean [Plain] = false  // Linha de incremento automático
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Business.WriteRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Source** : Data.DataTable [In]  // O que escrever
  - **Destination** : UiPath.Excel.IReadWriteRangeRef [In]  // Destino
- optional:
  - Append : Boolean [Plain] = false  // Acrescentar
  - ExcludeHeaders : Boolean [Plain] = false  // Excluir cabeçalhos
  - IgnoreEmptySource : Boolean [Plain]  // Ignorar origem vazia
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.CloseWorkbook
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.Workbook [In]
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.CreatePivotTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **UseTableSource** : Boolean [Plain]  // Usar origem da tabela
  - **PivotTableName** : String [In]  // Nome da nova tabela
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - SourceSheet : String [In]  // Planilha de Origem
  - SourceRange : String [In]  // Intervalo de origem
  - SourceTable : String [In]  // Nome da Tabela de Origem
  - PlacementCell : String [In]  // Célula de posicionamento dinâmico
  - LayoutRowType : UiPath.Excel.PivotTableLayoutRowType [In]  // Layout
  - ValuesMode : UiPath.Excel.PivotTableValuesMode [In]  // Values added as
  - PivotTableFields : Collections.Generic.List<Activities.InArgument<UiPath.Excel.PivotTableField>> [Plain]  // Campos de tabela dinâmica
  - PivotTableFieldsVariable : Collections.Generic.IEnumerable<UiPath.Excel.PivotTableField> [In]  // Variável de campos de tabela dinâmica
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.CreateTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : String [In]  // Intervalo
  - **TableName** : String [In]  // NomeDaTabela
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelAppendRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelApplicationScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **WorkbookPath** : String [In]  @group=New Workbook File  // Caminho da pasta de trabalho
  - **ExistingWorkbook** : UiPath.Excel.WorkbookApplication [In]  @group=Existing Workbook File  // PastaDeTrabalhoExistente
- optional:
  - Body : Activities.ActivityAction<UiPath.Excel.WorkbookApplication> [Plain]
  - Password : String [In]  // Senha
  - EditPassword : String [In]  // Editar senha
  - Visible : Boolean [Plain] = true  // Visível
  - CreateNewFile : Boolean [Plain] = true  // Criar se não existir
  - AutoSave : Boolean [Plain] = true  // Salvar alterações
  - ReadOnly : Boolean [Plain] = false  // SomenteLeitura
  - StartAsProcess : Boolean [Plain] = false  // Iniciar como um processo
  - MacroSetting : UiPath.Excel.MacroSetting [Plain] = 0  // MacroSetting
  - InstanceCachePeriod : Int32 [In]  // InstanceCachePeriod
  - SensitivityOperation : UiPath.Excel.ExcelLabelOperation [Plain]  // Operação de confidencialidade
  - SensitivityLabel : Object [In]  // Rótulo de confidencialidade
  - Workbook : UiPath.Excel.WorkbookApplication [Out]  // PastaDeTrabalho
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelAutoFillRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceRange** : String [In]  // IntervaloDeOrigem
  - **FillRange** : String [In]  // PreencherIntervalo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelCloseWorkbook
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.WorkbookApplication [In]  // PastaDeTrabalho
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelCopyPasteRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceRange** : String [In]  // Intervalo de origem
  - **DestinationSheet** : String [In]  // PlanilhaDeDestino
  - **DestinationCell** : String [In]  // CélulaDeDestino
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - CopyItems : UiPath.Excel.ExcelCopyOptions [Plain] = 15  // CopiarItens
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelCopySheet
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DestinationFilePath : String [In]  // CaminhoDoArquivoDeDestino
  - DestinationSheetName : String [In]  // NomeDaPlanilhaDeDestino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelCreatePivotTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceTableName** : String [In]  // Nome da Tabela de Origem
  - **Range** : String [In]  // Intervalo
  - **TableName** : String [In]  // NomeDaTabela
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelCreateTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : String [In]  // Intervalo
  - **TableName** : String [In]  // NomeDaTabela
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelDeleteColumn
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // NomeDaTabela
  - **ColumnName** : String [In]  // NomeDaColuna
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelDeleteRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : String [In]  // Intervalo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - ShiftCells : Boolean [Plain]  // DeslocarCélulas
  - ShiftOption : UiPath.Excel.ShiftOption [Plain]  // OpçãoDeDeslocamento
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelFilterTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // NomeDaTabela
  - **ColumnName** : String [In]  // NomeDaColuna
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - FilterOptions : String[] [In]  // OpçõesDeFiltro
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelGetCellColor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : String [In]  // Célula
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Color : Drawing.Color [Out]  // Cor
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelGetSelectedRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Range : String [Out]  // Intervalo
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelGetTableRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // NomeDaTabela
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - IsPivot : Boolean [Plain]  // ÉDinâmica
  - Range : String [Out]  // Intervalo
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelGetWorkbookSheet
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Index** : Int32 [In]  // Índice
- optional:
  - Sheet : String [Out]  // Planilha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelGetWorkbookSheets
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Sheets : Collections.Generic.List<String> [Out]  // Planilhas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelInsertColumn
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // NomeDaTabela
  - **ColumnName** : String [In]  // NomeDaColuna
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Position : Int32 [In]  // Posição
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelInsertDeleteColumns
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Position** : Int32 [In]  // Posição
  - **NoColumns** : Int32 [In]  // NenhumaColuna
  - **Mode** : UiPath.Excel.ChangeMode [Plain]  // AlterarModo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelInsertDeleteRows
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Position** : Int32 [In]  // Posição
  - **NoRows** : Int32 [In]  // NenhumaLinha
  - **Mode** : UiPath.Excel.ChangeMode [Plain]  // AlterarModo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelLookUpRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Value** : String [In]  // Valor
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Range : String [In]  // Intervalo
  - Result : String [Out]  // Resultado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelReadCell
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : String [In]  // Célula
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - PreserveFormat : Boolean [Plain] = false  // Usar formato de exibição
  - Result : ? [Out]  // Resultado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelReadCellFormula
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : String [In]  // Célula
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Formula : String [Out]  // Fórmula
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelReadColumn
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **StartingCell** : String [In]  // CélulaInicial
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - PreserveFormat : Boolean [Plain] = false  // Usar formato de exibição
  - Result : Collections.Generic.IEnumerable<Object> [Out]  // Resultado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelReadRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Range : String [In]  // Intervalo
  - DataTable : Data.DataTable [Out]  // TabelaDeDados
  - AddHeaders : Boolean [Plain]  // Adicionar Cabeçalhos
  - UseFilter : Boolean [Plain] = false  // UsarFiltro
  - PreserveFormat : Boolean [Plain] = false  // Usar formato de exibição
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelReadRow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **StartingCell** : String [In]  // CélulaInicial
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - PreserveFormat : Boolean [Plain] = false  // Usar formato de exibição
  - Result : Collections.Generic.IEnumerable<Object> [Out]  // Resultado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelRefreshPivotTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // NomeDaTabela
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelRemoveDuplicatesRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : String [In]  // Intervalo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelSaveWorkbook
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelSelectRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : String [In]  // Intervalo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelSetRangeColor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : String [In]  // Intervalo
  - **Color** : Drawing.Color [In]  // Cor
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelSortTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // NomeDaTabela
  - **ColumnName** : String [In]  // NomeDaColuna
  - **Order** : UiPath.Excel.OrderType [Plain]  // Ordem
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelWriteCell
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : String [In]  // Intervalo
  - **Text** : String [In]  // Valor
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExcelWriteRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - StartingCell : String [In]  // CélulaInicial
  - AddHeaders : Boolean [Plain]  // Adicionar Cabeçalhos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ExecuteMacro
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MacroName** : String [In]  // NomeDoMacro
- optional:
  - MacroParameters : Collections.Generic.IEnumerable<Object> [In]  // ParâmetrosDoMacro
  - MacroOutput : Object [Out]  // SaídaDoMacro
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Workbook : UiPath.Excel.Workbook [In]
  - WorkbookPath : String [In]
  - Password : String [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.GetCellColor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : String [In]  // Célula
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Color : Drawing.Color [Out]  // Cor
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.GetCellColorX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : UiPath.Excel.IReadCellRef [In]  // Célula
- optional:
  - OutputColor : Drawing.Color [Out]  // Cor salva
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.GetTableRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // NomeDaTabela
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - IsPivot : Boolean [Plain]  // ÉDinâmica
  - Range : String [Out]  // Intervalo
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.InvokeVBA
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **EntryMethodName** : String [In]  // NomeDoMétodoDeEntrada
  - **CodeFilePath** : String [In]  // CaminhoDoArquivoDeCódigo
- optional:
  - EntryMethodParameters : Collections.Generic.IEnumerable<Object> [In]  // ParâmetrosDoMétodoDeEntrada
  - OutputValue : Object [Out]  // ValorDeSaída
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Excel.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Description : String [Plain]

## UiPath.Excel.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]

## UiPath.Excel.Activities.OpenWorkbook
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **WorkbookPath** : String [In]
- optional:
  - Password : String [In]
  - Workbook : UiPath.Excel.Workbook [Out]
  - UseExcelApplication : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ReadCell
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : String [In]  // Célula
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - PreserveFormat : Boolean [Plain] = false  // Usar formato de exibição
  - Result : ? [Out]  // Resultado
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ReadCellFormula
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : String [In]  // Célula
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Result : String [Out]  // Resultado
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ReadColumn
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **StartingCell** : String [In]  // CélulaInicial
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - PreserveFormat : Boolean [Plain] = false  // Usar formato de exibição
  - Result : Collections.Generic.IEnumerable<Object> [Out]  // Resultado
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ReadRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Range : String [In] = "A1:A2"  // Intervalo
  - DataTable : Data.DataTable [Out]  // TabelaDeDados
  - AddHeaders : Boolean [Plain]  // Adicionar Cabeçalhos
  - PreserveFormat : Boolean [Plain] = false  // Usar formato de exibição
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.ReadRow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **StartingCell** : String [In]  // CélulaInicial
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - PreserveFormat : Boolean [Plain] = false  // Usar formato de exibição
  - Result : Collections.Generic.IEnumerable<Object> [Out]  // Resultado
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.SetRangeColor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : String [In]  // Intervalo
  - **Color** : Drawing.Color [In]  // Cor
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
  - **SheetName** : String [In]  // NomeDaPlanilha
- optional:
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Windows.Business.GetSelectedRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Workbook** : UiPath.Excel.IWorkbookQuickHandle [In]  // Pasta de trabalho de destino
- optional:
  - Range : UiPath.Excel.IReadRangeRef [Out]  // Intervalo
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.Windows.Business.SelectRangeX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Range** : UiPath.Excel.IReadRangeRef [In]  // Intervalo
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.WithWorkbook
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **WorkbookPath** : String [In]
- optional:
  - Password : String [In]
  - Workbook : UiPath.Excel.Workbook [Out]
  - Body : Activities.Activity [Plain]
  - UseExcelApplication : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.WriteCell
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Cell** : String [In]  // Célula
  - **Text** : String [In]  // Texto
  - **SheetName** : String [In]  // NomeDaPlanilha
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
- optional:
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Excel.Activities.WriteRange
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // TabelaDeDados
  - **SheetName** : String [In]  // NomeDaPlanilha
  - **WorkbookPath** : String [In]  @group=File  // Arquivo (caminho local)
  - **WorkbookPathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=FileResource  // Arquivo
- optional:
  - StartingCell : String [In] = "A1"  // CélulaInicial
  - AddHeaders : Boolean [Plain] = true  // Adicionar Cabeçalhos
  - Workbook : UiPath.Excel.Workbook [In]  @group=Use Workbook
  - Password : String [In]  // Senha
  - DisplayName : String [Plain]
  - Id : String [Plain]

