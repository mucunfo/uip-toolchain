# uipath.system.activities.runtime.portable
Assembly: UiPath.System.Activities v25.6.1.0
PackageVersion: 25.6.1
ActivityCount: 214

## UiPath.Activities.System.Agentic.RunAgent
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ProcessName** : String [In]  // Nome do agente
- optional:
  - BindingsKey : String [Plain]
  - FolderPath : String [In]  // Caminho da Pasta
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]
  - AgentArgumentsMetadata : UiPath.Orchestrator.Client.Models.ArgumentMetadata [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Arrays.AppendItemToList`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **List** : Collections.Generic.IList<T> [In]  // Lista
  - **ItemToAppend** : T [In]  // Item a acrescentar
- optional:
  - ItemIndex : Int32 [Out]  // Índice de itens
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Arrays.ReadListItem`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **List** : Collections.Generic.IList<T> [In]  // Lista
  - **ItemIndex** : Int32 [In]  // Índice de itens
- optional:
  - Value : T [Out]  // Salvar em
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Arrays.UpdateListItem`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **List** : Collections.Generic.IList<T> [In]  // Lista
  - **Value** : T [In]  // Novo valor
  - **ItemIndex** : Int32 [In]  // Índice de itens
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Collections.AppendItemToCollection`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Collection** : Collections.Generic.ICollection<T> [In]
  - **Items** : Collections.Generic.IEnumerable<Activities.InArgument<T>> [Plain]
- optional:
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Collections.BuildCollection`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FirstItem** : T [In]  // Primeiro item
- optional:
  - NextItems : Collections.Generic.List<Activities.InArgument<T>> [Plain]  // Próximos itens
  - Items : Collections.Generic.ICollection<T> [In]  // Itens
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Collections.ExistsInCollection`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Collection** : Collections.Generic.ICollection<T> [In]  // Coleção
  - **Item** : T [In]  // Item
- optional:
  - Exists : Boolean [Out]  // Existe
  - Index : Int32 [Out]  // Indexar se o item existir
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Collections.FilterCollection`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Collection** : Collections.Generic.ICollection<T> [In]  // Coleção
- optional:
  - FilterAction : UiPath.Activities.Collections.Filters.FilterAction [In]  // Filtrar ação
  - Filter : UiPath.Activities.Collections.Filters.CollectionFilterSettings [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Collections.MergeCollections`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Collection** : Collections.Generic.ICollection<T> [In]  // Coleção
  - **SecondCollection** : Collections.Generic.ICollection<T> [In]  // Segunda coleção
- optional:
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Collections.RemoveFromCollection`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Collection** : Collections.Generic.ICollection<T> [In]  // Coleção
- optional:
  - RemoveAllElements : Boolean [Plain]  // Remover Todos os Elementos
  - Item : T [In]  // Item
  - Index : Int32 [In]  // Índice
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Compression.Workflow.CompressFiles
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **CompressedFileName** : String [In]  // Nome do arquivo compactado
- optional:
  - ResourcesToArchive : Collections.Generic.IEnumerable<UiPath.Platform.ResourceHandling.IResource> [In]  // Recursos a compactar
  - ContentToArchive : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Conteúdo a compactar
  - AllowDuplicateContentNames : Boolean [In]  // Permitir conteúdos com nomes duplicados
  - Password : String [In]  @group=Password  // Senha
  - SecurePassword : Security.SecureString [In]  @group=Secure password  // Senha Segura
  - EncryptionAlgorithm : UiPath.Activities.Compression.Zip.ArchiveEncryptionAlgorithm [Plain]  // Algoritmo de criptografia
  - CompressionLevel : UiPath.Activities.Compression.Zip.ArchiveCompressionLevel [Plain]  // Nível de compactação
  - CodePage : UiPath.Activities.Encode.CodePages [Plain]  // Codificação de nome
  - OverrideExistingFile : Boolean [Plain]  // Substituir arquivo existente
  - CompressedFileInfo : IO.FileInfo [Out]  // Arquivo compactado
  - CompressedResource : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Referência do arquivo compactado
  - FilterFiles : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Compression.Workflow.ExtractFiles
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileToExtract** : String [In]  @group=FileToExtract  // Arquivo a extrair
  - **File** : UiPath.Platform.ResourceHandling.IResource [In]  @group=File  // Arquivo
- optional:
  - DestinationFolder : String [In]  // Pasta de destino
  - ExtractToADedicatedFolder : Boolean [Plain]  // Extrair para pasta dedicada
  - ConflictResolution : UiPath.Activities.FileOperations.FileConflictBehavior [In]  // Se os arquivos já existirem
  - Password : String [In]  // Senha
  - CodePage : UiPath.Activities.Encode.CodePages [Plain]  // Codificação de nome
  - SkipUnsupportedFiles : Boolean [Plain]  // Pular arquivos incompatíveis
  - DestinationFolderInfo : IO.DirectoryInfo [Out]  // Pasta de conteúdo extraído
  - Content : UiPath.Platform.ResourceHandling.ILocalResource[] [Out]  // Arquivos Extraídos
  - FilterFiles : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Date.AddOrSubtractFromDate
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Source** : DateTime [In]  // Data de origem
- optional:
  - SelectedOperation : UiPath.Activities.Date.AddOrSubtractFromDate/DateOperations [Plain]  // Operação
  - UnitOfTime : UiPath.Core.Activities.DateTimeUtilities.UnitsOfTime [Plain]  // Unidade
  - AmountOfTime : Int32 [In]  // Quantidade
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Date.FormatDateAsText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Format** : String [In]  // Formato da data e hora
  - **Source** : DateTime [In]  // Data de origem
- optional:
  - LocalizationCode : Globalization.CultureInfo [Plain]  // Código de localização
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Date.GetNextOrPreviousDate
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Source** : DateTime [In]  // Data de origem
- optional:
  - SelectedOperation : UiPath.Activities.Date.GetNextOrPreviousOperations [Plain]  // Operação
  - UnitOfTime : UiPath.Core.Activities.DateTimeUtilities.UnitsOfTime [Plain]  // Unidade
  - DayOfWeekSelection : DayOfWeek [Plain]  // Dia da semana
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.FileOperations.DownloadFileFromUrl
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Url** : String [In]  // URL
- optional:
  - FileName : String [In]  // Salvar arquivo como
  - ConflictResolution : UiPath.Activities.FileOperations.FileConflictBehavior [In]  // Se os arquivos já existirem
  - Timeout : Nullable<Int32> [In]  // Tempo Limite (segundos)
  - UserAgentHeader : String [In]  // Usuário agente
  - ResponseAttachment : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Arquivo baixado
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Jobs.RunJob
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ProcessName** : String [In]
- optional:
  - BindingsKey : String [Plain]
  - FolderPath : String [In]
  - Input : ? [In]
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]
  - ExecutionMode : UiPath.Activities.Jobs.JobExecutionMode [Plain]
  - ContinueOnError : Boolean [In]
  - TimeoutMS : Int32 [In]
  - FailWhenFaulted : Boolean [Plain]
  - Job : UiPath.Core.Activities.OrchestratorJob [Out]
  - Output : ? [Out]
  - ProcessType : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Jobs.StartJobAndGetReference
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FolderPath : String [Plain]
  - ProcessName : String [Plain]
  - ArgumentsJson : String [In]
  - JobOutput : UiPath.Core.Activities.OrchestratorJob [Out]
  - ProcessType : String [Out]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Jobs.WaitForJob
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - JobInput : UiPath.Core.Activities.OrchestratorJob [In]
  - Timeout : Int32 [Plain]
  - ContinueOnErrorProperty : Boolean [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Jobs.WaitForJobAndResume
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - JobInput : UiPath.Core.Activities.OrchestratorJob [In]
  - JobOutput : UiPath.Core.Activities.OrchestratorJob [Out]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [Plain]  // Continue On Error
  - WaitItemDataObject : TItem [InOut]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Orchestrator.Mail.SendEmailNotification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Subject** : String [In]
  - **Body** : String [In]
  - **Recipients** : Collections.Generic.IEnumerable<String> [In]
- optional:
  - TimeoutMS : Int32 [In]
  - ContinueOnError : Boolean [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Text.ChangeCase
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ChangeCaseOptions** : UiPath.Activities.Text.ChangeCaseOptions [Plain]  // Maiúsculas/minúsculas desejadas
  - **Source** : String [In]
- optional:
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Text.CombineText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Separator** : String [In]  // Separador
- optional:
  - Source : Collections.Generic.IEnumerable<String> [In]  // Valores de texto
  - SeparatorKey : UiPath.Activities.Text.SeparatorOptions [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Text.ExtractDateTime
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Format** : String [In]  // Formato da data e hora
  - **Source** : String [In]
- optional:
  - LocalizationCode : Globalization.CultureInfo [Plain]  // Código de localização
  - Results : Collections.Generic.IEnumerable<DateTime> [Out]  // Todaas as DataeHoras extraídas
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Text.ExtractText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ExtractOptions** : UiPath.Activities.Text.TextExtractOptions [Plain]  // O que extrair
  - **Source** : String [In]
- optional:
  - StartingText : String [In]  // Texto de início
  - EndingText : String [In]  // Texto de encerramento
  - IgnoreDuplicates : Boolean [Plain]  // Ignorar duplicatas
  - MatchCase : Boolean [Plain]  // Diferenciar maiúsculas/minúsculas
  - ExtractBaseURLOnly : Boolean [Plain]  // Extrair apenas URL base
  - FirstMatch : String [Out]
  - Results : Collections.Generic.IEnumerable<String> [Out]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Text.FindAndReplace
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Source** : String [In]
- optional:
  - ValueToFind : String [In]  // Valor a encontrar
  - ReplaceWith : String [In]  // Substituir por
  - MatchCase : Boolean [Plain]  // Diferenciar maiúsculas/minúsculas
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Activities.System.Text.SplitText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Separator** : String [In]  // Separador
  - **Source** : String [In]
- optional:
  - SeparatorKey : UiPath.Activities.Text.SeparatorOptions [Plain]
  - Results : Collections.Generic.IEnumerable<String> [Out]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ActionSchedulingMode
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.AddDataColumn`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // Tabela de Dados
  - **Column** : Data.DataColumn [In]  @group=Column  // Coluna
  - **ColumnName** : String [In]  @group=ColumnName  // Nome da Coluna
- optional:
  - AutoIncrement : Boolean [In]  // Incremento Automático
  - Unique : Boolean [In]  // Exclusivo
  - DefaultValue : T [In]  // ValorPadrão
  - AllowDBNull : Boolean [In]  // Permitir valores nulos
  - MaxLength : Int32 [In]  // TamanhoMáx
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.AddDataRow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [InOut]
  - **DataRow** : Data.DataRow [In]  @group=DataRow
  - **ArrayRow** : Object[] [In]  @group=ArrayRow
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.AddLogFields
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Fields : Collections.Generic.Dictionary<String,Activities.InArgument> [Plain]  // Campos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.AddQueueItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **QueueType** : String [In]  // Nome da fila
  - **ItemInformation** : Collections.Generic.Dictionary<String,Activities.InArgument> [Plain]  // Item Information
- optional:
  - BindingsKey : String [Plain]
  - Reference : String [In]  // Referência
  - ItemInformationCollection : Collections.Generic.Dictionary<String,Object> [In]  // Item Collection
  - Priority : UiPath.Core.QueueItemPriority [Plain]  // Prioridade
  - DeferDate : DateTime [In]  // Adiar
  - DueDate : DateTime [In]  // Prazo
  - ServiceBaseAddress : String [In]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - FolderPath : String [In]  // Caminho da Pasta
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.AddTransactionItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TransactionInformation** : Collections.Generic.Dictionary<String,Activities.InArgument> [Plain]  // Transaction Information
  - **QueueType** : String [In]  // Nome da fila
- optional:
  - Reference : String [In]  // Referência
  - FilterStrategy : UiPath.Core.Activities.ReferenceFilterStrategy [Plain] = 0
  - ServiceBaseAddress : String [In]
  - BindingsKey : String [Plain]
  - FolderPath : String [In]  // Caminho da Pasta
  - ContinueOnError : Boolean [In] = false  // Continue On Error
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - TransactionItem : UiPath.Core.QueueItem [Out]  // Transaction Item
  - SpecificData : ? [Out]  // Dados Específicos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.AlertSeverity
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.AppendLine
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  @group=FileName  // Nome do Arquivo
  - **File** : UiPath.Platform.ResourceHandling.ILocalResource [In]  @group=File  // Arquivo
  - **Text** : String [In]  // Texto
- optional:
  - Encoding : String [In]  // Codificação
  - UseDefaultEncoding : Boolean [In] = false  // Usar codificação padrão
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.AppLog
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Instance : UiPath.Core.Activities.AppLog [Plain]

## UiPath.Core.Activities.AssetValueType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.BooleanOperator
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.Break
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.BulkAddQueueItems
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **QueueItemsDataTable** : Data.DataTable [In]  // Tabela de Dados
  - **QueueName** : String [In]  // Nome da fila
- optional:
  - BindingsKey : String [Plain]
  - CommitType : UiPath.Core.Activities.BulkAddQueueItems/CommitTypeEnum [Plain] = 0  // Tipo De Confirmação
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.BusinessRuleParsingException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.BusinessTransactionsWrapper
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Disabled : Boolean [Plain]
  - Instance : UiPath.Core.Activities.IBusinessTransactionsWrapper [Plain]

## UiPath.Core.Activities.CacheStrategyEnum
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.CheckFalse
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Expression** : Boolean [In]  // Expressão
- optional:
  - ErrorMessage : String [In]  // MensagemDeErro
  - Result : Boolean [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CheckpointException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.CheckTrue
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Expression** : Boolean [In]  // Expressão
- optional:
  - ErrorMessage : String [In]  // MensagemDeErro
  - Result : Boolean [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ClearDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [InOut]  // Tabela de Dados
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CollectionToDataTable`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Collection** : Collections.Generic.ICollection<T> [In]  // Coleção
- optional:
  - DataTable : Data.DataTable [Out]  // Tabela de Dados
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Comment
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Text : String [Plain]  // Texto
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CommentOut
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Body : Activities.Activity [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ConnectionData
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - BearerToken : String [Plain]
  - Body : String [Plain]
  - Url : String [Plain]

## UiPath.Core.Activities.Continue
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CopyFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  // De
  - **Destination** : String [In]  // Para
- optional:
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Overwrite : Boolean [Plain] = false  // Substituir
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CopyFolderX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **From** : String [In]  // De
  - **To** : String [In]  // Para
- optional:
  - Overwrite : Boolean [Plain]  // Substituir
  - IncludeSubfolders : Boolean [Plain]  // Include subfolders
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CreateDirectory
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  // Caminho
- optional:
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Output : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Pasta
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CreateFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Path : String [In]
  - Name : String [In]
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Output : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Arquivo de Saída
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CurrentJobInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - WorkflowName : String [Plain]
  - ProcessName : String [Plain]
  - ProcessVersion : String [Plain]
  - RobotName : String [Plain]
  - Key : String [Plain]
  - TenantName : String [Plain]
  - FolderName : String [Plain]
  - UserEmail : String [Plain]
  - PictureInPictureMode : UiPath.Core.Activities.PictureInPictureMode [Plain]

## UiPath.Core.Activities.DateFormat
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.DateModifications.AddSubtractTimePeriodDateModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Value** : Int32 [In]  // Valor
- optional:
  - Operation : UiPath.Core.Activities.DateModifications.ModifyDateOperation [Plain] = 1  // Operação
  - TimeUnit : UiPath.Core.Activities.DateModifications.ModifyDateAddSubtractTimeUnit [Plain] = 0  // Unidade de Tempo
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.DateModifications.FindDayOfWeekDateModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Direction : UiPath.Core.Activities.DateModifications.FindDayOfWeekDirection [Plain] = 1  // Localizar
  - Day : DayOfWeek [Plain]  // Dia
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.DateModifications.FindStartEndDateModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Location : UiPath.Core.Activities.DateModifications.ModifyDateFirstLastDay [Plain] = -1  // Localizar
  - TimeUnit : UiPath.Core.Activities.DateModifications.ModifyDateFindFirstLastTimeUnit [Plain] = 0  // De
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Delete
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  @group=Path  // Caminho
  - **ResourceFile** : UiPath.Platform.ResourceHandling.ILocalResource [In]  @group=ResourceFile  // Arquivo
- optional:
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.DeleteQueueItems
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **QueueItems** : Collections.Generic.IEnumerable<UiPath.Core.QueueItem> [In]  // Queue Items
- optional:
  - FolderPath : String [In]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.DisableTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TriggerId** : String [Plain]
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.EnableTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TriggerId** : String [Plain]
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ErrorType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.EvaluateBusinessRule
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **BusinessRule** : String [In]  // Regra de Negócios
- optional:
  - BindingsKey : String [Plain]
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Argumentos
  - ArgumentsVariable : Collections.Generic.Dictionary<String,Object> [In]  // VariávelDeArgumentos
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da pasta do Orchestrator
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.FastRemovalQueue`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Count : Int32 [Plain]

## UiPath.Core.Activities.FileSystemException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.FileSystemLocalItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - LocalPath : String [Plain]
  - MimeType : String [Plain]
  - IconUri : String [Plain]
  - FullName : String [Plain]
  - ID : String [Plain]
  - IsFolder : Boolean [Plain]
  - CreationDate : Nullable<DateTime> [Plain]
  - LastModifiedDate : Nullable<DateTime> [Plain]
  - Metadata : Collections.Generic.Dictionary<String,String> [Plain]
  - IsResolved : Boolean [Plain]

## UiPath.Core.Activities.FilterDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // Tabela de Dados
- optional:
  - Filters : Collections.Generic.List<UiPath.Core.Activities.FilterOperationArgument> [Plain]
  - FilterRowsMode : UiPath.Core.Activities.SelectMode [In]
  - OutputFirstRow : Data.DataRow [Out]
  - SelectColumnsMode : UiPath.Core.Activities.SelectMode [In]  // SelecionarModoDeColunas
  - SelectColumns : Collections.Generic.List<Activities.InArgument> [Plain]
  - OutputDataTable : Data.DataTable [Out]  // Tabela de Dados
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.FilterOperationArgument
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Column : ? [In]
  - Operand : ? [In]
  - Operator : UiPath.Core.Activities.FilterOperator [Plain]
  - BooleanOperator : UiPath.Core.Activities.BooleanOperator [Plain]
  - IsStringOperation : Boolean [Plain]
  - IsEmptyOperation : Boolean [Plain]
  - IsFilterEmpty : Boolean [Plain]

## UiPath.Core.Activities.FilterOperator
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ForEach`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Values** : Collections.IEnumerable [In]  // Em
- optional:
  - Body : Activities.ActivityAction<T> [Plain]
  - Condition : Activities.Activity<Boolean> [Plain]  // Condição
  - MaxIterations : Int32 [In]  // IteraçõesMáx
  - CurrentIndex : Int32 [Out]  // Índice
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ForEachFileOrderByOptions
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ForEachFolderOrderByOptions
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ForEachRow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // Tabela de Dados
- optional:
  - ColumnCount : Int32 [Plain] = 9
  - ColumnNames : String [Plain]
  - ColumnSelectionType : UiPath.DataTableUtilities.DataColumnSelectionType [Plain] = 0
  - Body : Activities.ActivityAction<T> [Plain]
  - Values : Collections.IEnumerable [In]
  - Condition : Activities.Activity<Boolean> [Plain]  // Condição
  - MaxIterations : Int32 [In]  // IteraçõesMáx
  - CurrentIndex : Int32 [Out]  // Índice
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GenerateDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Input** : String [In]  @group=Use Text
  - **Positions** : Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>> [In]  @group=Use Positions
- optional:
  - DataTable : Data.DataTable [Out]
  - AutoDetectTypes : Boolean [Plain] = true
  - UseColumnHeader : Boolean [Plain] = false
  - UseRowHeader : Boolean [Plain] = false
  - ColumnSeparators : String [In]
  - NewLineSeparator : String [In]
  - CSVParsing : Boolean [In]
  - PreserveStrings : Boolean [Plain] = false
  - ColumnSizes : Collections.Generic.IEnumerable<Int32> [In]
  - PreserveNewLines : Boolean [Plain] = false
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetCurrentJobInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Result : UiPath.Core.Activities.CurrentJobInfo [Out]  // DadosDoTrabalho
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetJobs
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Filter : String [In]
  - FilterBuilder : UiPath.Activities.Jobs.JobFilterSettings [Plain]
  - Top : Int32 [In]
  - Skip : Int32 [In]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetLastDownloadedFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DownloadFolder** : String [In]  // Pasta de downloads
- optional:
  - Body : Activities.ActivityAction [Plain]
  - File : IO.FileInfo [Out]  // Arquivo baixado
  - FileResource : UiPath.Platform.ResourceHandling.ILocalResource [Out]
  - Timeout : Int32 [In]  // Tempo limite
  - IgnoreFiles : String [In]  // Ignorar extensões de arquivo
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetQueueItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **QueueType** : String [In]  // Nome da fila
- optional:
  - BindingsKey : String [Plain]
  - FolderPath : String [In]  // Caminho da Pasta
  - ContinueOnError : Boolean [In] = false  // Continue On Error
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - Reference : String [In]  // Referência
  - FilterStrategy : UiPath.Core.Activities.ReferenceFilterStrategy [Plain] = 0  // Filter Strategy
  - TransactionItem : UiPath.Core.QueueItem [Out]  // Transaction Item
  - SpecificData : ? [Out]  // Dados Específicos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetQueueItems
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **QueueName** : String [In]  // Nome da fila
- optional:
  - BindingsKey : String [Plain]
  - Reference : String [In]  // Referência
  - FilterStrategy : UiPath.Core.Activities.ReferenceFilterStrategy [Plain]  // Filter Strategy
  - QueueItemStates : UiPath.Core.Activities.QueueItemStates [Plain]  // Estados Dos Itens Na Fila
  - From : Nullable<DateTime> [In]  // De
  - To : Nullable<DateTime> [In]  // Para
  - Priority : Nullable<Int32> [In]
  - PriorityEnum : Nullable<UiPath.Core.QueueItemPriority> [Plain]  // Prioridade
  - Duration : Nullable<Int32> [In]  // Duração
  - Top : Int32 [In]  // Superior
  - Skip : Int32 [In]  // Pular
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetRobotAsset
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - BindingsKey : String [Plain]
  - Value : ? [Out]
  - AssetName : String [In]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - FolderPath : String [In]
  - CacheStrategy : UiPath.Core.Activities.CacheStrategyEnum [Plain]  // EstratégiaDeCache
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetRobotCredential
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - BindingsKey : String [Plain]
  - Username : String [Out]  // Nome de Usuário
  - Password : Security.SecureString [Out]  // Senha
  - AssetName : String [In]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - FolderPath : String [In]
  - CacheStrategy : UiPath.Core.Activities.CacheStrategyEnum [Plain]  // EstratégiaDeCache
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetRowItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Row** : Data.DataRow [In]  // Linha
  - **Value** : ? [Out]  // Valor
- optional:
  - ColumnIndex : Int32 [In]  // Número da coluna
  - ColumnName : String [In]  // Nome da Coluna
  - Column : Data.DataColumn [In]  // Coluna
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GlobalVariableChangedTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **VariableName** : Object [In]

## UiPath.Core.Activities.GlobalVariablesService
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Instance : UiPath.Core.Activities.GlobalVariablesService [Plain]

## UiPath.Core.Activities.GlobalVariableTriggerArgs
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Value : Object [Plain]

## UiPath.Core.Activities.IfElseIfBlock
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Condition : Boolean [In]
  - Then : Activities.Activity [Plain]
  - BlockType : UiPath.Core.Activities.IfElseIfBlockType [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.IfElseIfBlockType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.IfElseIfV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Condition : Boolean [In]
  - Then : Activities.Activity [Plain]
  - ElseIfs : ComponentModel.BindingList<UiPath.Core.Activities.IfElseIfBlock> [Plain]
  - Else : Activities.Activity [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.InterruptibleDoWhile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Body : Activities.Activity [Plain]
  - Condition : Activities.Activity<Boolean> [Plain]  // Condição
  - MaxIterations : Int32 [In]  // IteraçõesMáx
  - CurrentIndex : Int32 [Out]  // Índice
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.InterruptibleWhile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Body : Activities.Activity [Plain]
  - Condition : Activities.Activity<Boolean> [Plain]  // Condição
  - MaxIterations : Int32 [In]  // IteraçõesMáx
  - CurrentIndex : Int32 [Out]  // Índice
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.InvokeCode
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Code** : String [Plain]  // Código
- optional:
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Argumentos
  - Language : UiPath.Core.Activities.NetLanguage [Plain] = 0  // Idioma
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.InvokeProcess
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ProcessName** : String [In]  // Nome do processo
- optional:
  - BindingsKey : String [Plain]
  - FolderPath : String [In]  // Caminho da Pasta
  - EntryPointPath : String [In]  // Ponto de entrada
  - TargetSession : UiPath.Core.Activities.InvokeProcessTargetSession [Plain] = 0  // TargetSession
  - UsePackage : Boolean [Plain] = true  // Usar pacote
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Timeout : TimeSpan [In]  // Tempo Limite
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Argumentos
  - LogEntry : UiPath.Core.Activities.LogEntryType [In]  // Entrada de registro
  - LogExit : UiPath.Core.Activities.LogExitType [In]  // Saída de registro
  - ArgumentsVariable : Collections.Generic.Dictionary<String,Object> [In]  // VariávelDeArgumentos
  - Level : UiPath.Core.Activities.LogLevel [In]  // Nível de log
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.InvokeProcessTargetSession
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InvokeWorkflowFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **WorkflowFileName** : String [In]  // WorkflowFileName
- optional:
  - TargetSession : UiPath.Core.Activities.InvokeWorkflowTargetSession [Plain] = 0  // TargetSession
  - UnSafe : Boolean [Plain]  // Isolado
  - AssemblyName : String [Plain]
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Timeout : TimeSpan [In]  // Tempo Limite
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Argumentos
  - LogEntry : UiPath.Core.Activities.LogEntryType [In]  // Entrada de registro
  - LogExit : UiPath.Core.Activities.LogExitType [In]  // Saída de registro
  - ArgumentsVariable : Collections.Generic.Dictionary<String,Object> [In]  // VariávelDeArgumentos
  - Level : UiPath.Core.Activities.LogLevel [In]  // Nível de log
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.InvokeWorkflowRefactoringCore
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InvokeWorkflowTargetSession
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.IsMatch
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Pattern** : String [In]  // Padrão
  - **Input** : String [In]  // Texto no qual pesquisar
- optional:
  - RegexOption : Text.RegularExpressions.RegexOptions [Plain]  // Opções de padrão
  - TimeoutMS : Int32 [In]  // Tempo limite (ms)
  - Model : String [Plain]
  - BuilderPattern : String [Plain]
  - IsBuilderTabModified : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.JobState
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.JoinDataTables
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable1** : Data.DataTable [In]  // DataTable1
  - **DataTable2** : Data.DataTable [In]  // DataTable2
- optional:
  - Arguments : Collections.Generic.List<UiPath.Core.Activities.JoinOperationArgument> [Plain]
  - JoinType : UiPath.Core.Activities.JoinType [Plain]  // TipoDeJunção
  - OutputDataTable : Data.DataTable [Out]  // Tabela de Dados
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.JoinOperationArgument
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Column1 : ? [In]
  - Column2 : ? [In]
  - Operand : ? [In]
  - Operator : UiPath.Core.Activities.JoinOperator [Plain]
  - BooleanOperator : UiPath.Core.Activities.BooleanOperator [Plain]
  - IsJoinEmpty : Boolean [Plain]

## UiPath.Core.Activities.JoinOperator
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.JoinType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ListenForStopTriggers
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Description : String [Plain]

## UiPath.Core.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]

## UiPath.Core.Activities.LogEntryType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.LogExitType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.LogLevel
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.LogMessage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Message** : Object [In]  // Mensagem
- optional:
  - Level : UiPath.Core.Activities.LogLevel [In]  // NívelDeRegistro
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.LookupDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // Tabela de Dados
  - **LookupValue** : String [In]  // ValorDePesquisa
  - **LookupColumnIndex** : Nullable<Int32> [In]  @group=Lookup column index  // Número da coluna
  - **LookupColumnName** : String [In]  @group=Lookup column name  // Nome da Coluna
  - **LookupDataColumn** : Data.DataColumn [In]  @group=Lookup data column  // Coluna
- optional:
  - TargetColumnIndex : Nullable<Int32> [In]  // Número da coluna
  - TargetColumnName : String [In]  // Nome da Coluna
  - TargetDataColumn : Data.DataColumn [In]  // Coluna
  - CellValue : ? [Out]  // ValorDaCélula
  - RowIndex : Int32 [Out]  // ÍndiceDeLinha
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ManualTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Result : UiPath.Core.Activities.CurrentJobInfo [Out]  // DadosDoTrabalho
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Matches
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Pattern** : String [In]  // Padrão
  - **Input** : String [In]  // Texto no qual pesquisar
- optional:
  - RegexOption : Text.RegularExpressions.RegexOptions [Plain]  // Opções de padrão
  - TimeoutMS : Int32 [In]  // Tempo limite (ms)
  - FirstMatch : String [Out]  // Primeira correspondência
  - Model : String [Plain]
  - BuilderPattern : String [Plain]
  - IsBuilderTabModified : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.MergeDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Destination** : Data.DataTable [InOut]  // Destino
  - **Source** : Data.DataTable [In]  // Origem
- optional:
  - MissingSchemaAction : Data.MissingSchemaAction [Plain]  // AçãoDeEsquemaAusente
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ModifyDate
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceDate** : DateTime [In]  // Data a modificar
- optional:
  - FormatAsText : Boolean [Plain] = false  // Formatar saída como Texto
  - PredefinedDateFormat : UiPath.Core.Activities.DateFormat [Plain] = 0  // Formato da data
  - CustomDateFormat : String [In]  // Formato de data personalizado
  - UseCustomDateFormat : Boolean [Plain] = false  // Usar formato de data personalizado
  - OutDate : DateTime [Out]  // Salvar resultado como data/hora
  - OutText : String [Out]  // Salvar resultado como Texto
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ModifyDateDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DateModifications : Collections.Generic.List<UiPath.Core.Activities.IDateModificationModel> [Plain]

## UiPath.Core.Activities.ModifyText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SourceText** : String [In]  // Texto a modificar
  - **OutputText** : String [Out]  // Salvar resultado como
- optional:
  - Body : Activities.ActivityAction [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ModifyTextDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - TextModifications : Collections.Generic.List<UiPath.Core.Activities.ITextModificationModel> [Plain]

## UiPath.Core.Activities.MoveFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  @group=Path  // Caminho
  - **PathResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=PathResource  // Recurso de entrada
- optional:
  - Destination : String [In]  // Destino
  - DestinationResource : UiPath.Platform.ResourceHandling.IResource [In]  // Recurso de destino
  - Overwrite : Boolean [Plain] = false  // Substituir
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.MultipleFolderPathsException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.NetLanguage
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.NotifyGlobalVariableChanged
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **VariableName** : Object [In]
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OrchestratorAPIHttpMethods
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.OrchestratorHttpException
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - StatusCode : Net.HttpStatusCode [Plain]

## UiPath.Core.Activities.OrchestratorHttpRequest
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Method : UiPath.Core.Activities.OrchestratorAPIHttpMethods [Plain]  // Método
  - RelativeEndpoint : String [In]  // Relative Endpoint
  - JSONPayload : String [In]  // JSON Payload
  - StatusCode : Int32 [Out]  // CódigoDoStatus
  - ResponseHeaders : Collections.Generic.Dictionary<String,String> [Out]  // Cabeçalhos
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OrchestratorJob
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - StartTime : Nullable<DateTime> [Plain]
  - EndTime : Nullable<DateTime> [Plain]
  - State : UiPath.Core.Activities.JobState [Plain]
  - ProcessName : String [Plain]
  - Source : String [Plain]
  - EnvironmentName : String [Plain]
  - PackageName : String [Plain]
  - Key : Nullable<Guid> [Plain]
  - OutputArguments : String [Plain]
  - Info : String [Plain]

## UiPath.Core.Activities.OutputDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // Tabela de Dados
- optional:
  - Text : String [Out]  // Texto
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.PasswordCredentials
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Target : String [Plain]
  - DisplayName : String [Plain]
  - Password : String [Plain]
  - SecurePassword : Security.SecureString [Plain]
  - Username : String [Plain]

## UiPath.Core.Activities.PathExists
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  // Caminho
- optional:
  - PathType : UiPath.Core.Activities.PathType [Plain]  // TipoDeCaminho
  - Exists : Boolean [Out]  // Existe
  - Resource : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Referenciar se o caminho existir
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.PathType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.PictureInPictureMode
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.Placeholder
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Description : String [Plain]  // Descrição
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.PostponeTransactionItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TransactionItem** : UiPath.Core.QueueItem [In]  // Transaction Item
- optional:
  - DeferDate : DateTime [In]  // Adiar
  - DueDate : DateTime [In]  // Prazo
  - ContinueOnError : Boolean [In] = false  // Continue On Error
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - FolderPath : String [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ProcessTracking.ProcessTrackingScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ProcessLogMode : UiPath.Activities.ProcessTracking.ProcessTrackingMode [Plain]
  - ProcessCaseName : String [In]
  - TaskName : String [In]
  - ProcessCaseNameToSwitchTo : String [In]
  - ObjectId : String [In]
  - ObjectType : String [In]
  - ObjectInteraction : UiPath.Activities.ProcessTracking.PTSObjectInteraction [In]
  - Sequence : Activities.Activity [Plain]
  - ScopeId : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ProcessTracking.SetTaskStatus
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Status** : UiPath.Activities.ProcessTracking.TaskStatus [In]  // Status
- optional:
  - TaskGuid : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ProcessTracking.SetTraceStatus
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Status** : UiPath.Activities.ProcessTracking.TraceStatus [In]  // Status
- optional:
  - TraceGuid : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ProcessTracking.TrackObject
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ObjectType** : String [In]
  - **ObjectId** : String [In]
- optional:
  - ObjectInteraction : UiPath.Activities.ProcessTracking.PTSObjectInteraction [In]
  - ObjectPropertiesV2 : Collections.Generic.Dictionary<String,Object> [In]
  - ObjectProperties : Collections.Generic.Dictionary<String,String> [In]
  - UseObjectPropertiesV2 : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ProcessTriggerArgs
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ProcessInfo : UiPath.Core.ProcessInfo [Plain]

## UiPath.Core.Activities.ProxyCredential
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Username : String [Plain]
  - Password : String [Plain]

## UiPath.Core.Activities.QueueItemStates
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.QueueTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DefaultOutArgumentVariableName : String [Plain]
  - FolderPath : String [Plain]  // Caminho da Pasta
  - QueueName : String [Plain]  // Nome da fila
  - BindingsKey : String [Plain]
  - ItemsActivationThreshold : Int32 [Plain]
  - ItemsPerJobActivationTarget : Int32 [Plain]
  - MaxJobsForActivation : Int32 [Plain]
  - TransactionItem : UiPath.Core.QueueItem [Out]  // Transaction Item
  - ExtractedQueueItem : ? [Out]  // Dados Específicos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RaiseAlert
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Notification** : String [In]  // Notificação
- optional:
  - Severity : UiPath.Core.Activities.AlertSeverity [Plain]  // Gravidade
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da pasta do Orchestrator
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ReadTextFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  @group=FileName  // Nome do Arquivo
  - **File** : UiPath.Platform.ResourceHandling.IResource [In]  @group=File  // Arquivo
- optional:
  - Encoding : String [In]  // Codificação
  - Content : String [Out]  // Saída em
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RefactoringsCore
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ProcessTrackingScopeType : Type [Plain]
  - MorphModelItem : Action<Activities.Presentation.Model.ModelItem> [Plain]
  - InvokeWorkflow : UiPath.Activities.Contracts.InvokeWorkflowRefactoring [Plain]
  - EnableDisable : UiPath.Activities.Contracts.EnableDisableRefactoring [Plain]

## UiPath.Core.Activities.ReferenceFilterStrategy
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.RemoveDataColumn
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [InOut]  // Da tabela de dados
  - **ColumnIndex** : Int32 [In]  @group=ColumnIndex  // Número da coluna
  - **ColumnName** : String [In]  @group=ColumnName  // Nome da Coluna
- optional:
  - Column : Data.DataColumn [In]  // Coluna
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RemoveDataRow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [InOut]
  - **RowIndex** : Int32 [In]  @group=RowIndex
  - **Row** : Data.DataRow [In]  @group=Row
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RemoveDuplicateRows
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // Tabela de Dados
- optional:
  - OutputDataTable : Data.DataTable [Out]  // Tabela de Dados
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RemoveLogFields
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Fields : Collections.Generic.List<Activities.InArgument<String>> [Plain]  // Campos
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RepeatNumberOfTimesX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **NumberOfTimes** : Int32 [In]  // Número de Vezes
- optional:
  - Body : Activities.ActivityAction<Int32> [Plain]
  - StartAt : Int32 [In] = "System.Activities.InArgument`1<System.Int32>"  // Iniciar às
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RepeatTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Interval** : TimeSpan [In]

## UiPath.Core.Activities.RepeatTriggerArgs
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - EventTimestamp : DateTime [Plain]

## UiPath.Core.Activities.Replace
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Pattern** : String [In]  // Padrão
  - **Input** : String [In]  // Texto para substituir
  - **Replacement** : String [In]  // Substituir por texto
- optional:
  - RegexOption : Text.RegularExpressions.RegexOptions [Plain]  // Opções de padrão
  - TimeoutMS : Int32 [In]  // Tempo limite (ms)
  - Model : String [Plain]
  - BuilderPattern : String [Plain]
  - IsBuilderTabModified : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ReportStatus
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **StatusText** : Object [In]  // TextoDoStatus
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ResetTimer
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Timer** : UiPath.Core.Timer [In]  // Temporizador
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ResumeTimer
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Timer** : UiPath.Core.Timer [In]  // Temporizador
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RetryScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Condition : Activities.ActivityFunc<Boolean> [Plain]
  - NumberOfRetries : Int32 [In]  // Número de tentativas
  - RetryInterval : TimeSpan [In]  // IntervaloDeRepetição
  - ContinueOnError : Boolean [In]  // Continue On Error
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Return
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RobotAssetModel
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Name : String [Plain]
  - ValueType : UiPath.Core.Activities.AssetValueType [Plain]
  - Value : String [Plain]
  - StringValue : String [Plain]
  - BoolValue : Boolean [Plain]
  - IntValue : Int32 [Plain]
  - CredentialUsername : String [Plain]
  - CredentialPassword : String [Plain]
  - ConnectionData : UiPath.Core.Activities.ConnectionData [Plain]

## UiPath.Core.Activities.SelectMode
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.SetAsset
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **AssetName** : String [In]  // Asset Name
  - **Value** : Object [In]  // Valor
- optional:
  - BindingsKey : String [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da pasta do Orchestrator
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetCredential
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **CredentialName** : String [In]  // Nome do ativo da Credential
  - **UserName** : String [In]  // Nome de Usuário
  - **Password** : String [In]  @group=Normal password  // Senha
  - **SecurePassword** : Security.SecureString [In]  @group=Secure password  // Senha Segura
- optional:
  - BindingsKey : String [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da pasta do Orchestrator
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetTransactionProgress
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TransactionItem** : UiPath.Core.QueueItem [In]  // Transaction Item
  - **Progress** : String [In]  // Progresso
- optional:
  - FolderPath : String [In]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetTransactionStatus
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TransactionItem** : UiPath.Core.QueueItem [In]  // Transaction Item
- optional:
  - Status : UiPath.Core.ProcessingStatus [Plain]  // Status
  - Output : Collections.Generic.Dictionary<String,Activities.InArgument> [Plain]  // Saída
  - Analytics : Collections.Generic.Dictionary<String,Activities.InArgument> [Plain]  // Analytics
  - Reason : String [In]  // Motivo
  - Details : String [In]  // Detalhes
  - ErrorType : UiPath.Core.Activities.ErrorType [Plain]  // TipoDeErro
  - AssociatedFilePath : String [In]  // CaminhoDoArquivoAssociado
  - ContinueOnError : Boolean [In] = false  // Continue On Error
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - FolderPath : String [In]
  - ServiceBaseAddress : String [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ShouldStop
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SortDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DataTable** : Data.DataTable [In]  // Tabela de Dados
- optional:
  - ColumnIndex : Nullable<Int32> [In]  // Índice
  - ColumnName : String [In]  // Nome
  - DataColumn : Data.DataColumn [In]  // Coluna
  - Order : UiPath.Core.Activities.SortingOrder [Plain]
  - SortOrder : UiPath.Core.Activities.SortOrder [Plain]  // Ordenar
  - OutputDataTable : Data.DataTable [Out]  // Tabela de Dados
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SortingOrder
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.SortOrder
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.StartJob
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ProcessName** : String [In]  // Nome do processo
- optional:
  - BindingsKey : String [Plain]
  - NumberOfRobots : Int32 [In]  // Número de robôs
  - ModernFolder : Boolean [In] = true  // Modern Folder
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Argumentos
  - ArgumentsVariable : Collections.Generic.Dictionary<String,Object> [In]  // VariávelDeArgumentos
  - JobPriority : UiPath.Orchestrator.Client.Models.StartProcessDtoJobPriority [In]  // Prioridade do Trabalho
  - ResumeOnSameContext : Boolean [In]  // Retomar no mesmo contexto
  - Key : String [Out]  // ID do Processo
  - JobId : String [Out]  // ID do Trabalho
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da pasta do Orchestrator
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.StartTimer
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Timer** : UiPath.Core.Timer [Out]  // Temporizador
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.StartTriggers
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **WorkflowFileName** : String [In]  // WorkflowFileName
- optional:
  - TargetSession : UiPath.Core.Activities.InvokeWorkflowTargetSession [Plain] = 0  // TargetSession
  - UnSafe : Boolean [Plain]  // Isolado
  - AssemblyName : String [Plain]
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Timeout : TimeSpan [In]  // Tempo Limite
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Argumentos
  - LogEntry : UiPath.Core.Activities.LogEntryType [In]  // Entrada de registro
  - LogExit : UiPath.Core.Activities.LogExitType [In]  // Saída de registro
  - ArgumentsVariable : Collections.Generic.Dictionary<String,Object> [In]  // VariávelDeArgumentos
  - Level : UiPath.Core.Activities.LogLevel [In]  // Nível de log
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.StopJob
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Job** : UiPath.Core.Activities.OrchestratorJob [In]
- optional:
  - FolderPath : String [In]
  - Strategy : UiPath.Core.Activities.StopStrategy [In]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.StopStrategy
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.StopTimer
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Timer** : UiPath.Core.Timer [In]  // Temporizador
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.StopTriggers
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - StoppingTriggers : Threading.AutoResetEvent [Plain]
  - ShouldStop : Boolean [Out]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Storage.DeleteStorageFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  // Caminho
  - **StorageBucketName** : String [In]  // Nome do Bucket de Armazenamento
- optional:
  - BindingsKey : String [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da pasta do Orchestrator
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Storage.DownloadStorageFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  // Caminho
  - **StorageBucketName** : String [In]  // Nome do Bucket de Armazenamento
- optional:
  - Destination : String [In]  // Nome e local do arquivo
  - BindingsKey : String [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Storage.ListStorageFiles
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Directory** : String [In]  // Diretório
  - **StorageBucketName** : String [In]  // Nome do Bucket de Armazenamento
- optional:
  - Filter : String [In]  // Filter
  - Recursive : Boolean [In]  // Recursivo
  - BindingsKey : String [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Storage.ReadStorageText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  // Caminho
  - **StorageBucketName** : String [In]  // Nome do Bucket de Armazenamento
- optional:
  - Encoding : String [In]  // Codificação
  - BindingsKey : String [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Storage.UploadStorageFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  @group=Path  // Caminho
  - **FileResource** : UiPath.Platform.ResourceHandling.IResource [In]  @group=File  // Arquivo
  - **Destination** : String [In]  // Destino
  - **StorageBucketName** : String [In]  // Nome do Bucket de Armazenamento
- optional:
  - BindingsKey : String [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da pasta do Orchestrator
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Storage.WriteStorageText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  // Caminho
  - **Text** : String [In]  // Texto
  - **StorageBucketName** : String [In]  // Nome do Bucket de Armazenamento
- optional:
  - Encoding : String [In]  // Codificação
  - BindingsKey : String [Plain]
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da pasta do Orchestrator
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SystemXamlMigration
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - NamespacesToRemove : Collections.Generic.IEnumerable<String> [Plain]
  - NamespacesToAdd : Collections.Generic.IEnumerable<String> [Plain]
  - AssemblyReferencesToRemove : Collections.Generic.IEnumerable<String> [Plain]
  - AssemblyReferencesToAdd : Collections.Generic.IEnumerable<String> [Plain]

## UiPath.Core.Activities.TextModifications.CombineTextModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **NewText** : String [In]  // Novo texto a adicionar
- optional:
  - InsertionSide : UiPath.Core.Activities.TextModifications.TextInsertionSide [Plain] = 0  // Adicionar novo texto a
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TextModifications.FindAndReplaceTextModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SearchText** : String [In]  // Pesquisar
- optional:
  - ReplaceText : String [In]  // Substituir por
  - MatchCase : Boolean [Plain] = false  // Diferenciar maiúsculas/minúsculas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TextModifications.ToUpperLowerTextModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ModificationType : UiPath.Core.Activities.TextModifications.UpperLowerModificationType [Plain] = 0  // Alterar texto para
  - UseCurrentCulture : Boolean [Plain] = true  // Usar cultura atual
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TextModifications.TrimTextModification
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - TrimBefore : Boolean [Plain] = true  // Cortar à esquerda
  - TrimAfter : Boolean [Plain] = true  // Cortar à direita
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TextToLeftRight
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FullText** : String [In]  // Texto a ser dividido
  - **Separator** : String [In]  // Separador
- optional:
  - SeparatorKey : UiPath.Core.Activities.TextToLeftRight/DefaultSeparators [Plain]
  - CustomSeparatorEnabled : Boolean [Plain] = true
  - TextToLeft : String [Out]  // Texto extraído antes do separador
  - TextToRight : String [Out]  // Texto extraído após o separador
  - CaseSensitiveSeparator : Boolean [Plain] = true  // Separador com diferenciação de maiúsculas/minúsculas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TimeoutScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ThrowExceptionAfter** : TimeSpan [In]  // Lançar exceção após
- optional:
  - Body : Activities.ActivityAction<Activities.Activity> [Plain]
  - TimeoutMessage : String [In]  // Mensagem de tempo limite esgotado
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TimeTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - TimeZone : String [Plain]
  - Frequency : UiPath.Core.Activities.TimeTrigger/TimeFrequency [Plain]
  - MinuteByMinuteRepeat : Nullable<Int32> [Plain]
  - HourlyRepeat : Nullable<Int32> [Plain]
  - HourlyStartingMinutes : Nullable<Int32> [Plain]
  - DailyRepeat : Nullable<Int32> [Plain]
  - DailyStartingTime : Nullable<DateTime> [Plain]
  - WeeklyDaysToRunOn : Collections.Generic.List<DayOfWeek> [Plain]
  - WeeklyStartingTime : Nullable<DateTime> [Plain]
  - MonthlyRepeat : Nullable<Int32> [Plain]
  - MonthDaySelection : UiPath.Core.Activities.TimeTrigger/MonthDaySelectionType [Plain]
  - DaysOfMonthToRunOn : Collections.Generic.List<String> [Plain]
  - MonthlyDaysToRunOn : Collections.Generic.List<DayOfWeek> [Plain]
  - MonthlyStartingTime : Nullable<DateTime> [Plain]
  - CronExpression : String [Plain]
  - Result : UiPath.Core.Activities.CurrentJobInfo [Out]  // DadosDoTrabalho
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TriggerRefactoringCore
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.TriggerScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - SchedulingMode : UiPath.Core.Activities.ActionSchedulingMode [Plain]  // ModoDeAgendamento
  - ContinueOnError : Boolean [In]  // Continue On Error
  - Triggers : Collections.Generic.List<Activities.Activity> [Plain]
  - Variables : Collections.ObjectModel.Collection<Activities.Variable> [Plain]
  - AllowedItemType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.UpdateRowItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Value** : Object [In]  // Valor
  - **Row** : Data.DataRow [In]  // Linha
- optional:
  - ColumnIndex : Int32 [In]  // Número da coluna
  - ColumnName : String [In]  // Nome da Coluna
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.WaitQueueItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **QueueName** : String [In]  // Nome da fila
- optional:
  - BindingsKey : String [Plain]
  - PollTimeMS : Int32 [In]  // PollTime (milissegundos)
  - Reference : String [In]  // Referência
  - FilterStrategy : UiPath.Core.Activities.ReferenceFilterStrategy [Plain]  // Filter Strategy
  - TimeoutMS : Int32 [In]  // Tempo Limite (milissegundos)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.WriteTextFile
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  @group=FileName  // Nome do Arquivo
  - **File** : UiPath.Platform.ResourceHandling.ILocalResource [In]  @group=File  // Arquivo
  - **Text** : String [In]  // Texto
- optional:
  - Encoding : String [In]  // Codificação
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.BusinessRuleException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.CurrencyNumberFormatProvider
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Symbol : String [Plain]
  - DecimalSeparator : String [Plain]
  - GroupSeparator : String [Plain]
  - DecimalDigits : Int32 [Plain]
  - DisplayName : String [Plain]
  - Pattern : String [Plain]

## UiPath.Core.DateTimeFormatProvider
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Pattern : String [Plain]
  - DisplayName : String [Plain]

## UiPath.Core.FileChangeInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ChangeType : IO.WatcherChangeTypes [Plain]
  - FullPath : String [Plain]
  - Name : String [Plain]
  - OldFullPath : String [Plain]
  - OldName : String [Plain]

## UiPath.Core.GeneralNumberFormatProvider
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DecimalSeparator : String [Plain]
  - GroupSeparator : String [Plain]
  - DecimalDigits : Int32 [Plain]
  - Pattern : String [Plain]
  - DisplayName : String [Plain]

## UiPath.Core.GenericValue
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FormatProvider : IFormatProvider [Plain]

## UiPath.Core.GenericValueTypeConverter
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.PercentageNumberFormatProvider
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Symbol : String [Plain]
  - DecimalSeparator : String [Plain]
  - GroupSeparator : String [Plain]
  - DecimalDigits : Int32 [Plain]
  - DisplayName : String [Plain]
  - Pattern : String [Plain]

## UiPath.Core.ProcessInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Name : String [Plain]
  - ProcessId : UInt32 [Plain]
  - ParentProcessId : UInt32 [Plain]
  - CommandLine : String [Plain]
  - ExecutablePath : String [Plain]
  - CreationDate : DateTime [Plain]
  - Handle : String [Plain]
  - HasExited : Boolean [Plain]

## UiPath.Core.ProcessingException
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Reason : String [Plain]
  - Details : String [Plain]
  - Type : UiPath.Core.ProcessingExceptionType [Plain]
  - AssociatedImageFilePath : String [Plain]
  - Id : Int64 [Plain]
  - CreationTime : Nullable<DateTime> [Plain]

## UiPath.Core.ProcessingExceptionType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.ProcessingStatus
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.QueueItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Id : Nullable<Int64> [Plain]
  - Progress : String [Plain]
  - SpecificContent : Collections.Generic.Dictionary<String,Object> [Plain]
  - Reference : String [Plain]
  - QueueName : String [Plain]
  - RetryNo : Int32 [Plain]
  - Status : UiPath.Core.QueueItemStatus [Plain]
  - LastProcessingOn : String [Plain]
  - ItemKey : Guid [Plain]
  - QueueDefinitionId : Int64 [Plain]
  - AssignedTo : String [Plain]
  - Priority : UiPath.Core.QueueItemPriority [Plain]
  - RowVersion : Byte[] [Plain]
  - ProcessingException : UiPath.Core.ProcessingException [Plain]
  - StartTransactionTime : Nullable<DateTime> [Plain]
  - ReviewStatus : String [Plain]
  - Output : Collections.Generic.Dictionary<String,Object> [Plain]
  - DueDate : Nullable<DateTime> [Plain]
  - DeferDate : Nullable<DateTime> [Plain]
  - ParentOperationId : String [Plain]
  - UniqueKey : Nullable<Guid> [Plain]

## UiPath.Core.QueueItemPriority
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.QueueItemStatus
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Timer
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Elapsed : TimeSpan [Plain]
  - ElapsedMilliseconds : Int64 [Plain]
  - IsRunning : Boolean [Plain]
  - ElapsedTicks : Int64 [Plain]

