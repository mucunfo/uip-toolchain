# uipath.testing.activities
Assembly: UiPath.Testing.Activities v25.10.2.0
PackageVersion: 25.10.2
ActivityCount: 25

## UiPath.Testing.Activities.AddTestDataQueueItem
- required:
  - **QueueName** : String [In]  // Nome da fila
- optional:
  - IsDesign : Boolean [Plain]
  - Items : Collections.ObjectModel.ObservableCollection<UiPath.Testing.Activities.ActivityItemContainer> [Plain]
  - ActivityToAdd : UiPath.Testing.Activities.ActivityItemContainer [Plain]
  - FolderPath : String [In]  // Caminho da Pasta
  - TimeoutMs : Int32 [In]  // Tempo limite (milésimos de segundo)
  - ArgumentsBridgeActivityCollection : Collections.Generic.List<Activities.ActivityFunc<Object>> [Plain]
  - ShowOutputArgumentCheckBoxes : Boolean [Plain]
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.ArgumentsBridge
- optional:
  - Input : Object [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.AttachDocument
- required:
  - **FilePath** : String [In]  // Arquivo
- optional:
  - Tags : Collections.Generic.IEnumerable<String> [In]  // Tags
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.BulkAddTestDataQueue
- required:
  - **QueueItemsDataTable** : Data.DataTable [In]  // TabelaDeDados
  - **QueueName** : String [In]  // Nome da fila
- optional:
  - ContinueOnError : Boolean [In]  // Continue On Error
  - FolderPath : String [In]  // Caminho da Pasta
  - TimeoutMs : Int32 [In]  // Tempo limite (milésimos de segundo)
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.ComparePdfDocuments
- required:
  - **BaselinePath** : UiPath.Platform.ResourceHandling.IResource [In]  // Caminho da linha de base
  - **TargetPath** : UiPath.Platform.ResourceHandling.IResource [In]  // Caminho de destino
  - **ComparisonType** : UiPath.Testing.Activities.Models.ComparisonType [Plain]  // Tipo de comparação
  - **OutputFolderPath** : String [In]  // Caminho da pasta de saída
- optional:
  - ContinueOnFailure : Boolean [In]  // ContinuarComFalha
  - InterpretDifferencesWithAutopilot : Boolean [Plain] = false  // Interpretar diferenças com o Autopilot
  - Rules : Collections.Generic.List<Activities.InArgument<UiPath.Testing.Activities.Models.ComparisonRule>> [Plain]  // Regras
  - RulesList : Collections.Generic.List<UiPath.Testing.Activities.Models.ComparisonRule> [In]  // Regras
  - Differences : Collections.Generic.IEnumerable<UiPath.Testing.Activities.Models.Difference> [Out]  // Diferenças
  - Result : Boolean [Out]  // Resultado
  - SemanticDifferences : UiPath.Testing.Activities.Models.SemanticDifferences [Out]  // Diferenças semânticas
  - IgnoreIdenticalItems : Boolean [In]  // Ignorar itens idênticos
  - IncludeImages : Boolean [In]  // Incluir widgets
  - IgnoreImagesLocation : Boolean [In]  // Ignorar localização dos widgets
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.CompareText
- required:
  - **BaselineText** : String [In]  // Texto de linha de base
  - **TargetText** : String [In]  // Texto de destino
  - **OutputFilePath** : String [In]  // Caminho do arquivo de saída
  - **ComparisonType** : UiPath.Testing.Activities.Models.ComparisonType [Plain]  // Tipo de comparação
- optional:
  - ContinueOnFailure : Boolean [In]  // ContinuarComFalha
  - Rules : Collections.Generic.List<Activities.InArgument<UiPath.Testing.Activities.Models.ComparisonRule>> [Plain]  // Regras
  - RulesList : Collections.Generic.List<UiPath.Testing.Activities.Models.ComparisonRule> [In]  // Regras
  - InterpretDifferencesWithAutopilot : Boolean [Plain] = false  // Interpretar diferenças com o Autopilot
  - WordSeparators : String [In]  // Separadores de palavras
  - Differences : Collections.Generic.IEnumerable<UiPath.Testing.Activities.Models.Difference> [Out]  // Diferenças
  - Result : Boolean [Out]  // Resultado
  - SemanticDifferences : UiPath.Testing.Activities.Models.SemanticDifferences [Out]  // Diferenças semânticas
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.Coverage.CoverageMergeActivity
- required:
  - **TestSetExecutionId** : Int64 [In]
  - **PackageId** : String [In]
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.CreateComparisonRule
- optional:
  - RuleName : String [In]  // Nome da Regra
  - UsePlaceholder : Boolean [In]  // Usar espaço reservado
  - ComparisonRuleType : UiPath.Testing.Activities.Models.ComparisonRuleType [Plain]  // Tipo de regra de comparação
  - Pattern : String [In]  // Padrão
  - ContinueOnError : Boolean [In]  // Continue On Error
  - ComparisonRule : UiPath.Testing.Activities.Models.ComparisonRule [Out]  // Regra de comparação 
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.DeleteTestDataQueueItems
- required:
  - **TestDataQueueItems** : Collections.Generic.List<UiPath.Testing.Core.TestDataQueueItem> [In]  // Itens de Fila de Dados de Teste
- optional:
  - FolderPath : String [In]  // Caminho da Pasta
  - TimeoutMs : Int32 [In]  // Tempo limite (milésimos de segundo)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.GetTestDataQueueItem
- required:
  - **QueueName** : String [In]  // Nome da fila
  - **Output** : Collections.Generic.Dictionary<String,Object> [Out]  // Output
- optional:
  - MarkConsumed : Boolean [Plain]  // Marcar como consumido
  - FolderPath : String [In]  // Caminho da Pasta
  - TimeoutMs : Int32 [In]  // Tempo limite (milésimos de segundo)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.GetTestDataQueueItems
- required:
  - **QueueName** : String [In]  // Nome da fila
  - **TestDataQueueItems** : Collections.Generic.List<UiPath.Testing.Core.TestDataQueueItem> [Out]  // Output
- optional:
  - IdFilter : String [In]  // ID do filtro
  - TestDataQueueItemStatus : UiPath.Testing.Activities.TestDataQueues.Enums.TestDataQueueItemStatus [Plain]  // Status dos itens da fila
  - Top : Nullable<Int32> [In]  // Superior
  - Skip : Nullable<Int32> [In]  // Pular
  - FolderPath : String [In]  // Caminho da Pasta
  - TimeoutMs : Int32 [In]  // Tempo limite (milésimos de segundo)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.Mocks.MockActivity
- optional:
  - MockedActivity : Activities.Activity [Plain]
  - MockedActivityIdRef : String [Plain]
  - Mock : Activities.Activity [Plain]
  - MockedActivityScreenShotBase64 : String [Plain]
  - IsMockedActivityScreenShotVisible : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.NewAddTestDataQueueItem
- required:
  - **QueueName** : String [In]  // Nome da fila
  - **ItemInformation** : Collections.Generic.Dictionary<String,Activities.InArgument> [Plain]  // Itens
- optional:
  - FolderPath : String [In]  // Caminho da Pasta
  - TimeoutMs : Int32 [In]  // Tempo limite (milésimos de segundo)
  - ContinueOnError : Boolean [In]  // Continue On Error
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.QueryEntitiesFilterActivity
- required:
  - **EntityName** : String [In]  // Entity Name
- optional:
  - Filters : String [In]  // Filtros
  - ExpansionDepth : Nullable<Int32> [In]  // Nível de expansão
  - ArgumentIdentifier : String [In]  // O identificador do argumento
  - OutputPath : String [Out]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.TestData.Address
- optional:
  - Country : String [In]  // País
  - City : String [In]  // Cidade
  - AddressResult : Collections.Generic.Dictionary<String,String> [Out]  // Address
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.TestData.GivenName
- optional:
  - GivenNameResult : String [Out]  // Primeiro nome
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.TestData.LastName
- optional:
  - LastNameResult : String [Out]  // Sobrenome
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.TestData.RandomDate
- required:
  - **MinDate** : DateTime [In]  // Data mínima
  - **MaxDate** : DateTime [In]  // Data máxima
- optional:
  - Output : DateTime [Out]  // Saída
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.TestData.RandomNumber
- optional:
  - Min : Int64 [In]  // Mín.
  - Max : Int64 [In]  // Máx.
  - Decimals : Int32 [In]  // Casas Decimais
  - Output : Decimal [Out]  // Saída
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.TestData.RandomString
- required:
  - **Case** : UiPath.Testing.Enums.Case [Plain]  // Caso
  - **Length** : Int32 [In]  // Tamanho
- optional:
  - Output : String [Out]  // Saída
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.TestData.RandomValue
- required:
  - **FilePath** : String [In]  // Arquivo
- optional:
  - Value : String [Out]  // Generate Random Value
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.VerifyControlAttribute
- required:
  - **Operator** : UiPath.Testing.Comparison [Plain]  // Operador
  - **Expression** : ? [In]  // Expressão
  - **OutputArgument** : String [Plain]
  - **ActivityToTest** : Activities.ActivityAction [Plain]
- optional:
  - ArgumentsBridgeActivity : Activities.ActivityFunc<Object> [Plain]
  - OutputMessageFormat : String [In]  // FormatoDeMensagemDeSaída
  - TakeScreenshotInCaseOfSucceedingAssertion : Boolean [In]
  - TakeScreenshotInCaseOfFailingAssertion : Boolean [In]
  - ContinueOnFailure : Boolean [In]  // ContinuarComFalha
  - AlternativeVerificationTitle : String [In]  // TítuloDeVerificaçãoAlternativo
  - Result : Boolean [Out]  // Resultado
  - KeepScreenshots : Boolean [In]
  - ScreenshotsPath : String [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.VerifyExpression
- required:
  - **Expression** : Boolean [In]  // Expressão
- optional:
  - OutputMessageFormat : String [In]  // FormatoDeMensagemDeSaída
  - TakeScreenshotInCaseOfSucceedingAssertion : Boolean [In]
  - TakeScreenshotInCaseOfFailingAssertion : Boolean [In]
  - ContinueOnFailure : Boolean [In]  // ContinuarComFalha
  - AlternativeVerificationTitle : String [In]  // TítuloDeVerificaçãoAlternativo
  - Result : Boolean [Out]  // Resultado
  - KeepScreenshots : Boolean [In]
  - ScreenshotsPath : String [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.VerifyExpressionWithOperator
- required:
  - **FirstExpression** : ? [In]  // PrimeiraExpressão
  - **SecondExpression** : ? [In]  // SegundaExpressão
  - **Operator** : UiPath.Testing.Comparison [Plain]  // Operador
- optional:
  - OutputMessageFormat : String [In]  // FormatoDeMensagemDeSaída
  - TakeScreenshotInCaseOfSucceedingAssertion : Boolean [In]
  - TakeScreenshotInCaseOfFailingAssertion : Boolean [In]
  - ContinueOnFailure : Boolean [In]  // ContinuarComFalha
  - AlternativeVerificationTitle : String [In]  // TítuloDeVerificaçãoAlternativo
  - Result : Boolean [Out]  // Resultado
  - KeepScreenshots : Boolean [In]
  - ScreenshotsPath : String [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Testing.Activities.VerifyRange
- required:
  - **Expression** : ? [In]  // Expressão
  - **VerificationType** : UiPath.Testing.Activities.VerificationType [Plain]  // TipoDeVerificação
  - **LowerLimit** : ? [In]  // LimiteMínimo
  - **UpperLimit** : ? [In]  // LimiteMáximo
- optional:
  - OutputMessageFormat : String [In]  // FormatoDeMensagemDeSaída
  - TakeScreenshotInCaseOfSucceedingAssertion : Boolean [In]
  - TakeScreenshotInCaseOfFailingAssertion : Boolean [In]
  - ContinueOnFailure : Boolean [In]  // ContinuarComFalha
  - AlternativeVerificationTitle : String [In]  // TítuloDeVerificaçãoAlternativo
  - Result : Boolean [Out]  // Resultado
  - KeepScreenshots : Boolean [In]
  - ScreenshotsPath : String [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

