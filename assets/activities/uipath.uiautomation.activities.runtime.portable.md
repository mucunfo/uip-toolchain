# uipath.uiautomation.activities.runtime.portable
Assembly: UiPath.UIAutomationNext.Activities v25.10.16.0
PackageVersion: 25.10.16
ActivityCount: 201

## UiPath.Core.Activities.AncestryInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - TopDownHierarchy : Collections.Generic.List<UiPath.Core.Activities.NodeInfo> [Plain]

## UiPath.Core.Activities.NodeInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - IsInSelector : Boolean [Plain]
  - IndexInSiblings : Int32 [Plain]
  - UiNodeObj : UiPath.UiNode [Plain]
  - Siblings : Collections.Generic.IReadOnlyList<UiPath.UiNode> [Plain]
  - SiblingStart : Int32 [Plain]
  - SiblingCount : Int32 [Plain]

## UiPath.Core.Activities.NodeSelectorInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Idx : Int32 [Plain]
  - XmlString : String [Plain]

## UiPath.Core.Browser
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Element : UiPath.Core.UiElement [Plain]

## UiPath.Core.EventInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Image
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.UiElement
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Semantic.Activities.NExtractFormDataGeneric`1
- xmlns: `http://schemas.uipath.com/workflow/activities/uix, http://schemas.uipath.com/workflow/activities`
- optional:
  - FieldMappings : Collections.Generic.IDictionary<String,String> [Plain]
  - FormData : T [Out]  // Dados do Formulário
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Semantic.Activities.NFillForm
- xmlns: `http://schemas.uipath.com/workflow/activities/uix, http://schemas.uipath.com/workflow/activities`
- optional:
  - DataSource : Object [In]  // Fonte de Dados
  - EnableValidation : Boolean [Plain] = false  // Habilitar validação
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Semantic.Activities.NSetValue
- xmlns: `http://schemas.uipath.com/workflow/activities/uix, http://schemas.uipath.com/workflow/activities`
- optional:
  - Value : String [In]  // Valor
  - EnableValidation : Boolean [Plain] = false  // Habilitar validação
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Semantic.Activities.NUITask
- xmlns: `http://schemas.uipath.com/workflow/activities/uix, http://schemas.uipath.com/workflow/activities`
- optional:
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Task : String [In]  // Tarefa
  - AgentType : UiPath.UIAutomationNext.Enums.NUITaskAgentType [In]  // Tipo de agente
  - Result : String [Out]  // Resultado
  - CustomConfiguration : String [In]  // Configuração personalizada
  - ClipboardMode : UiPath.UIAutomationNext.Enums.NTypeByClipboardMode [In]  // Digitar pela área de transferência
  - MaxIterations : Int32 [In]  // Número máximo de etapas
  - IsDOMEnabled : Boolean [In]
  - ExecutionTrace : String [Out]
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NApplicationCard
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Body : Activities.ActivityAction<Object> [Plain]
  - TargetApp : UiPath.UIAutomationNext.TargetApp [Plain]  // Destino do Aplicativo Unificado
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - Timeout : Double [In]  // Tempo Limite
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - InteractionMode : UiPath.UIAutomationNext.Enums.NInteractionMode [Plain] = 2  // Modo de entrada
  - AttachMode : UiPath.UIAutomationNext.Enums.NAppAttachMode [Plain] = 0  // Modo de anexação de janela
  - OpenMode : UiPath.UIAutomationNext.Enums.NAppOpenMode [In]  // Abrir
  - CloseMode : UiPath.UIAutomationNext.Enums.NAppCloseMode [In]  // Fechar
  - WindowResize : UiPath.UIAutomationNext.Enums.NWindowResize [Plain] = 0  // Redimensionar janela
  - UserDataFolderMode : UiPath.UIAutomationNext.Enums.BrowserUserDataFolderMode [In]  // Modo da pasta de dados do usuário
  - UserDataFolderPath : String [In]  // Caminho da pasta de dados do usuário
  - IsIncognito : Boolean [In]  // Janela anônima/privada
  - WebDriverMode : UiPath.UIAutomationNext.Enums.NWebDriverMode [In]  // Modo do WebDriver
  - DialogHandling : UiPath.UIAutomationNext.DialogHandling [Plain]  // Manuseio de caixas de diálogo
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NHealingAgentBehavior [In]  // Modo do Healing Agent
  - Version : UiPath.UIAutomationNext.Enums.NApplicationCardVersion [Plain] = 0
  - IsDisplayNameAuto : Boolean [Plain] = false
  - ScopeIdentifier : String [Plain]
  - ScopeGuid : String [Plain]
  - ConnectionId : String [In]
  - ConnectionName : String [Plain]
  - ConnectorType : String [Plain] = "z-uipath-browser"
  - IsAuthenticationRequired : Boolean [Plain] = false
  - IsCVEnabled : Nullable<Boolean> [Plain]
  - AutoGenerationOptions : UiPath.UIAutomationNext.Models.GenerationOptions [Plain]
  - IsIndicateOnDesktopEnabled : Boolean [Plain] = false
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NBlockUserInput
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayBefore : Double [In]
  - DelayAfter : Double [In]
  - Timeout : Double [In]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - BlockType : UiPath.UIAutomationNext.Enums.NBlockInputType [In]
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]
  - Keys : String [In]
  - DisableUnblock : Boolean [In]
  - Allow3rdPartyApps : Boolean [In]
  - Body : Activities.Activity [Plain]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NBrowserDialogScope
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DialogMessage : String [Out]  // Mensagem da caixa de diálogo
  - DelayAfter : Double [In]
  - DialogScopeType : UiPath.UIAutomationNext.Enums.NBrowserDialogScopeType [Plain] = 0  // Tipo de caixa de diálogo
  - DialogResponse : UiPath.UIAutomationNext.Enums.NBrowserDialogResponse [In]  // Resposta da caixa de diálogo
  - PromptDialogResponseText : String [In]  // Texto de resposta do prompt
  - WaitForDialogToAppearTimeout : Double [In]  // Esperar a caixa de diálogo aparecer no tempo limite
  - Body : Activities.Activity [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Tempo Limite
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NBrowserFilePickerScope
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayAfter : Double [In]
  - Mode : UiPath.UIAutomationNext.Enums.NBrowserFilePickerScopeMode [Plain] = 0  // Modo
  - SingleFilePath : String [In]  // Caminho do arquivo
  - MultiFilePaths : Collections.Generic.List<String> [In]  // Caminhos do Arquivo
  - WaitForDialogToAppearTimeout : Double [In]  // Esperar a caixa de diálogo aparecer no tempo limite
  - Body : Activities.Activity [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Tempo Limite
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NCheck
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Action : UiPath.UIAutomationNext.Enums.NCheckType [In]  // Ação
  - AlterIfDisabled : Boolean [In]  // Alterar elemento desabilitado
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NCheckElement
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Result : Boolean [Out]  // Habilitado(a)
  - DelayBefore : Double [In]
  - DelayAfter : Double [In]
  - Timeout : Double [In]  // Tempo Limite
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NCheckState
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayAfter : Double [In]
  - ContinueOnError : Boolean [In]
  - Exists : Boolean [Out]  // Resultado
  - Timeout : Double [In]  // Tempo limite (segundos)
  - Mode : UiPath.UIAutomationNext.Enums.NCheckStateMode [Plain] = 0  // Aguardar (aparecer/desaparecer)
  - CheckVisibility : Boolean [Plain] = false  // Verificar visibilidade
  - IfExists : Activities.Activity [Plain]
  - IfNotExists : Activities.Activity [Plain]
  - EnableIfExists : Boolean [Plain] = true
  - EnableIfNotExists : Boolean [Plain] = true
  - IsLoose : Boolean [Plain] = false
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NClick
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Modificadores de tecla
  - ClickType : UiPath.UIAutomationNext.Enums.NClickType [In]  // Tipo de clique
  - MouseButton : UiPath.UIAutomationNext.Enums.NMouseButton [In]  // Botão do mouse
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // Tipo de movimento do cursor
  - VerifyOptions : UiPath.UIAutomationNext.Activities.VerifyExecutionOptions [Plain]  // Verificar execução
  - AlterIfDisabled : Boolean [In]  // Alterar elemento desabilitado
  - ActivateBefore : Boolean [In]  // Ativar
  - UnblockInput : Boolean [In]  // DesbloquearEntrada
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NClickTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Button : UiPath.UIAutomationNext.Enums.NMouseButton [In]  // Botão do mouse
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Modificadores de tecla
  - BlockEvent : Boolean [In]  // BloquearEvento
  - IncludeChildren : Boolean [In]  // IncludeChildren
  - Mode : UiPath.UIAutomationNext.Triggers.NClickTriggerMode [In]  // ModoDeDisparo
  - SchedulingMode : UiPath.Platform.Triggers.TriggerActionSchedulingMode [Plain]  // ModoDeAgendamento
  - Enabled : Boolean [Plain]
  - ContinueOnError : Boolean [In]
  - Timeout : Double [In]
  - DelayAfter : Double [In]
  - DelayBefore : Double [In]
  - InUiElement : UiPath.Core.UiElement [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - IsSchedulingModeAvailable : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]

## UiPath.UIAutomationNext.Activities.NClosePopup
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - PopupException : Exception [In]  // Exceção detectada no pop-up
  - PreferredButtons : String[] [In]  // Botões para fechar pop-up
  - PopupHandled : UiPath.UIAutomationNext.Enums.NPopupHandleState [Out]  // Pop-up gerenciado
  - PopupAppearTimeout : Double [In]  // Tempo limite de exibição do pop-up
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]
  - EnableAI : Boolean [Plain] = false  // Modo avançado de IA
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NDragAndDrop
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Modificadores de tecla
  - MouseButton : UiPath.UIAutomationNext.Enums.NMouseButton [In]  // Botão do mouse
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // Tipo de movimento do cursor
  - DestinationTarget : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Alvo de Destino
  - DestinationScopeIdentifier : String [Plain]
  - DestinationInScope : Object [In]
  - UseSourceHover : Boolean [In]  // Focalizar elemento de origem
  - DelayBetweenActions : Double [In]  // Atraso entre ações
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NExtractData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- required:
  - **ExtractMetadata** : String [In]  // Extrair metadados
- optional:
  - DataTable : Data.DataTable [InOut]  // TabelaDeDados
  - LimitExtractionTo : UiPath.UIAutomationNext.Models.ExtractData.LimitType [Plain]  // Limitar a extração a
  - MaximumResults : Int32 [In]  // Número de itens
  - NextLink : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino (botão Avançar)
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - DelayBetweenPages : Double [In]  // Atraso entre as páginas
  - ExtractSimilar : Boolean [Plain]
  - AppendResults : Boolean [Plain] = true  // Acrescentar resultados
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - ExtractDataSettings : String [In]  // Configurações da tabela
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NExtractDataGeneric`1
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- required:
  - **ExtractMetadata** : String [In]  // Extrair metadados
- optional:
  - AppendResults : Boolean [Plain] = false
  - InputDataTable : Data.DataTable [In]  // TabelaDeDados de Entrada
  - ExtractedData : T [Out]  // TabelaDeDados
  - LimitExtractionTo : UiPath.UIAutomationNext.Models.ExtractData.LimitType [Plain]  // Limitar a extração a
  - MaximumResults : Int32 [In]  // Número de itens
  - NextLink : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino (botão Avançar)
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - DelayBetweenPages : Double [In]  // Atraso entre as páginas
  - ExtractSimilar : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - ExtractDataSettings : String [In]  // Configurações da tabela
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NForEachUiElement
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Variables : Collections.ObjectModel.Collection<Activities.Variable> [Plain]
  - VariablesMetadata : Collections.Generic.Dictionary<String,Collections.Generic.List<UiPath.UIAutomationNext.Activities.Models.VariableMetadata>> [Plain]
  - Body : Activities.ActivityAction<Int32> [Plain]
  - Filter : UiPath.UIAutomationNext.Activities.Models.FilterArgument [Plain]
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - NextLink : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino (botão Avançar)
  - ExtractMetadata : String [In]  // Metadados de elementos de interface gráfica
  - ExtractDataSettings : String [In]  // Configurações dos elementos de interface gráfica
  - LimitExtractionTo : UiPath.UIAutomationNext.Models.ExtractData.LimitType [Plain]  // Limitar a extração a
  - MaximumResults : Int32 [In]  // Número de itens
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - DelayBetweenPages : Double [In]  // Atraso entre as páginas
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Result : ? [Out]
  - Attribute : String [In]  // Atributo
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetAttributeGeneric`1
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Result : T [Out]  // Salvar em
  - Attribute : String [In]  // Atributo
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetBrowserData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Browser : UiPath.Core.Browser [In]  // Navegador
  - BrowserType : UiPath.UIAutomationNext.Enums.NBrowserType [In]  // Tipo de navegador
  - SourceUserDataFolder : String [In]  // Pasta de dados do Usuário de Origem
  - UserProfile : String [In]  // Perfil do Usuário
  - SessionData : String [Out]  // Dados da Sessão
  - Timeout : Double [In]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetClipboard
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Result : String [Out]  // Saída em
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetText
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DisableExternalTools : Boolean [Plain]
  - ScrapingOptions : UiPath.UIAutomationNext.Enums.NScrapingOptions [In]
  - ScrapingMethod : UiPath.UIAutomationNext.Enums.NScrapingMethod [Plain] = 0  // Método de coleta
  - Text : ? [Out]  // Texto
  - TextString : String [Out]  // Texto
  - WordsInfo : Collections.Generic.IEnumerable<UiPath.UIAutomationNext.Activities.Models.NWordInfo> [Out]  // Informações sobre palavras
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetUrl
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - WaitForReady : UiPath.UIAutomationNext.Enums.NWaitForReady [In]  // Aguardar carregamento da página
  - CurrentUrl : String [Out]  // URL Atual
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGoToUrl
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Url : String [In]  // URL
  - Mode : UiPath.UIAutomationNext.Enums.NGoToUrlMode [Plain] = 0  // Modo
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NHighlight
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - HighlightTime : Double [In]  // Duração
  - Color : Drawing.Color [Plain]  // Cor
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NHover
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - HoverTime : Double [In]  // Duração
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // Tipo de movimento do cursor
  - VerifyOptions : UiPath.UIAutomationNext.Activities.VerifyExecutionOptions [Plain]  // Verificar execução
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NInjectJsScript
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - InputParameter : String [In]  // Parâmetro de entrada
  - ScriptCode : String [In]  // Código do script
  - ScriptOutput : ? [Out]  // Saída do script
  - ExecutionWorld : UiPath.UIAutomationNext.Enums.NExecutionWorld [In]  // Mundo de execução
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NKeyboardShortcuts
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ActivateBefore : Boolean [In]  // Ativar
  - DelayBetweenShortcuts : Double [In]  // Atraso entre atalhos
  - DelayBetweenKeys : Double [In]  // Atraso entre teclas
  - ClickBeforeMode : UiPath.UIAutomationNext.Enums.NClickMode [In]  // Clicar antes de digitar
  - ShortcutsArgument : String [In]  // Atalhos
  - Shortcuts : String [Plain]  // Atalhos
  - VerifyOptions : UiPath.UIAutomationNext.Activities.VerifyExecutionOptions [Plain]  // Verificar execução
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NKeyboardTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Key : String [In]  // Chave
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Modificadores de tecla
  - BlockEvent : Boolean [In]  // BloquearEvento
  - IncludeChildren : Boolean [In]  // IncludeChildren
  - Mode : UiPath.UIAutomationNext.Triggers.NKeyTriggerMode [In]  // ModoDeDisparo
  - SchedulingMode : UiPath.Platform.Triggers.TriggerActionSchedulingMode [Plain]  // ModoDeAgendamento
  - Enabled : Boolean [Plain]
  - ContinueOnError : Boolean [In]
  - Timeout : Double [In]
  - DelayAfter : Double [In]
  - DelayBefore : Double [In]
  - InUiElement : UiPath.Core.UiElement [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - IsSchedulingModeAvailable : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]

## UiPath.UIAutomationNext.Activities.NMouseScroll
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Direction : UiPath.UIAutomationNext.Enums.NScrollDirection [In]  // Direção
  - MovementUnits : Int32 [In]  // Nº de rolagens
  - SearchedElement : UiPath.UIAutomationNext.Activities.SearchedElement [Plain]  // Elemento pesquisado
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // Tipo de movimento do cursor
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Modificadores de tecla
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NNativeEventTrigger`1
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - EventType : UiPath.UIAutomationNext.Triggers.NNativeEventType [Plain] = 0  // Tipo de Evento
  - AvailableEventTypes : String [Plain]
  - MatchSync : Boolean [Plain] = false  // Sincronização de correspondência
  - IncludeChildren : Boolean [In]  // IncludeChildren
  - Selectors : Collections.Generic.IEnumerable<String> [In]  // Seletores
  - SchedulingMode : UiPath.Platform.Triggers.TriggerActionSchedulingMode [Plain]  // ModoDeAgendamento
  - Enabled : Boolean [Plain]
  - ContinueOnError : Boolean [In]
  - Timeout : Double [In]
  - DelayAfter : Double [In]
  - DelayBefore : Double [In]
  - InUiElement : UiPath.Core.UiElement [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - IsSchedulingModeAvailable : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]

## UiPath.UIAutomationNext.Activities.NNavigateBrowser
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Action : UiPath.UIAutomationNext.Enums.NNavigateBrowserAction [Plain] = 0  // Ação
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPCallTransaction
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Transaction : String [In]  // Código da Transação
  - Prefix : String [In]  // Prefixo
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPClickPictureOnScreen
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Modificadores de tecla
  - ClickType : UiPath.UIAutomationNext.Enums.NClickType [In]  // Tipo de clique
  - AlterIfDisabled : Boolean [In]  // Alterar elemento desabilitado
  - ActivateBefore : Boolean [In]  // Ativar
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPClickToolbarButton
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Item : String [In]  // Botão da Barra de Ferramentas
  - Items : Collections.Generic.List<String> [Plain]
  - AlterIfDisabled : Boolean [In]  // Alterar elemento desabilitado
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPExpandALVTree
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Path : String [In]  // Caminho de Árvore
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPExpandTree
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Item : String [In]  // Item de Árvore
  - Items : Collections.Generic.List<String> [Plain]
  - AlterIfDisabled : Boolean [In]  // Alterar elemento desabilitado
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPLogin
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Username : String [In]  // Nome de usuário
  - SecurePassword : Security.SecureString [In]  // SenhaSegura
  - Password : String [In]  // Senha
  - Client : String [In]  // Cliente
  - Language : String [In]  // Idioma
  - Option : UiPath.UIAutomationNext.Enums.NMultiLogonOption [Plain]  // Opção de Logon Múltiplos
  - IsSecure : Boolean [Plain] = false  // É Segura
  - OutUiElement : UiPath.Core.UiElement [Out]  // Janela de Sessão do SAP
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPReadStatusbar
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - MessageType : String [Out]  // Tipo de Mensagem
  - MessageText : String [Out]  // Texto de Mensagem
  - MessageId : String [Out]  // IdDaMensagem
  - MessageNumber : String [Out]  // NúmeroDaMensagem
  - MessageData : String[] [Out]  // Dados de Mensagem
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPSelectDatesInCalendar
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - SelectType : UiPath.UIAutomationNext.Enums.NDateSelectionType [In]  // Selecionar tipo
  - Date : DateTime [In]  // Data
  - StartDate : DateTime [In]  // Data de Início
  - EndDate : DateTime [In]  // Data de Término
  - Year : Int32 [In]  // Ano
  - Week : Int32 [In]  // Semana
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPSelectMenuItem
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Item : String [In]  // Item de Menu
  - AlterIfDisabled : Boolean [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Items : Collections.Generic.List<String> [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPTableCellScope
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ColumnName : String [In]  // Nome da coluna/filtro
  - RowIndex : UInt32 [In]  // Índice de linha
  - RowSelector : String [In]  // Seletor de linha
  - RowType : UiPath.UIAutomationNext.Enums.NSAPTableCellScopeRowType [In]  // Tipo de entrada de linha
  - TableRow : UInt32 [Out]  // Índice de Linhas da Tabela
  - ColumnNames : Collections.Generic.IEnumerable<String> [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSaveUserDataFolder
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - UserDataFolder : String [Plain]
  - ConnectionName : String [In]
  - AssetName : String [Plain]
  - ConnectionId : String [In]
  - Description : String [In]
  - Url : String [In]
  - CreatedAssetName : String [Out]
  - ContinueOnError : Boolean [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSelectItem
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Item : String [In]  // Item
  - Items : Collections.Generic.List<String> [Plain]
  - AlterIfDisabled : Boolean [In]  // Alterar elemento desabilitado
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSetClipboard
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Text : String [In]  // Texto
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSetFocus
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSetRuntimeBrowser
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - BrowserType : UiPath.UIAutomationNext.Enums.NBrowserType [In]  // Tipo de navegador
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSetText
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Text : String [In]  // Texto
  - CacheTargetElement : Boolean [Plain] = false  // Armazene em cache o elemento de destino
  - AlterIfDisabled : Boolean [In]  // Alterar elemento desabilitado
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NTakeScreenshot
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayBeforeScreenshot : Double [In]  // Atraso antes de captura de tela
  - FileName : String [In]  // Nome do arquivo
  - FileNameMode : UiPath.UIAutomationNext.Enums.NFileNameMode [In]  // Incremento automático
  - SavedTo : ? [Out]  // Caminho do arquivo salvo
  - OutImage : UiPath.Core.Image [Out]  // Imagem salva
  - SaveScreenshotTo : UiPath.UIAutomationNext.Enums.NSaveScreenshotTo [Plain] = 0
  - DelayAfter : Double [In]
  - OutFile : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Arquivo salvo
  - Timeout : Double [In]  // Tempo Limite
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NTypeInto
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DisableExternalTools : Boolean [Plain]
  - Text : String [In]  // Texto
  - SecureText : Security.SecureString [In]  // Texto seguro
  - DelayBetweenKeys : Double [In]  // Atraso entre teclas
  - ActivateBefore : Boolean [In]  // Ativar
  - ClickBeforeMode : UiPath.UIAutomationNext.Enums.NClickMode [In]  // Clicar antes de digitar
  - EmptyFieldMode : UiPath.UIAutomationNext.Enums.NEmptyFieldMode [In]  // Campo vazio
  - ClipboardMode : UiPath.UIAutomationNext.Enums.NTypeByClipboardMode [In]  // Digitar pela área de transferência
  - DeselectAfter : Boolean [In]  // Desmarcar no final
  - IsPassword : Boolean [Plain] = false
  - VerifyOptions : UiPath.UIAutomationNext.Activities.VerifyExecutionTypeIntoOptions [Plain]  // Verificar execução
  - AlterIfDisabled : Boolean [In]  // Alterar elemento desabilitado
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Modo de entrada
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NUnblockUserInput
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NWindowOperation
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Operation : UiPath.UIAutomationNext.Enums.NWindowOperationType [In]  // Operação
  - X : Int32 [In]  // X
  - Y : Int32 [In]  // Y
  - Width : Int32 [In]  // Largura
  - Height : Int32 [In]  // Altura
  - Timeout : Double [In]  // Tempo Limite
  - DelayAfter : Double [In]  // Atraso após
  - DelayBefore : Double [In]  // Atraso antes
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // Continuar com erro
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Modo do Healing Agent
  - InUiElement : UiPath.Core.UiElement [In]  // Elemento de entrada
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.SearchedElement
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DisplayName : String [Plain]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - Timeout : Double [In]  // Tempo Limite
  - OutUiElement : UiPath.Core.UiElement [Out]  // Elemento de saída

## UiPath.UIAutomationNext.Activities.SupportsSpecialKeysAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Activities.Triggers.DownloadChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - State : String [Plain]
  - Id : String [Plain]
  - FileName : String [Plain]
  - Url : String [Plain]
  - StartTime : String [Plain]
  - EndTime : String [Plain]
  - Error : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.EmptyArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.HtmlWindowBoundsChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - WindowId : String [Plain]
  - Focused : Boolean [Plain]
  - Top : Int32 [Plain]
  - Left : Int32 [Plain]
  - Width : Int32 [Plain]
  - Height : Int32 [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.HtmlWindowCreatedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - WindowId : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.HtmlWindowFocusChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - TabId : String [Plain]
  - WindowId : String [Plain]
  - Title : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.HtmlWindowRemovedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - WindowId : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.HwndArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - HwndAsString : String [Plain]
  - Hwnd : IntPtr [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.JavaCellSelectedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Row : Int32 [Plain]
  - Column : Int32 [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.JavaCellValueChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Row : Int32 [Plain]
  - Column : Int32 [Plain]
  - Value : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.JavaKeyPressArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - KeyChar : String [Plain]
  - KeyCode : Int32 [Plain]
  - ExtendedKeyCode : Int32 [Plain]
  - Location : String [Plain]
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.JavaMouseActionArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - X : Int32 [Plain]
  - Y : Int32 [Plain]
  - Button : Int32 [Plain]
  - ClickCount : Int32 [Plain]
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.JavaMouseMotionArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - X : Int32 [Plain]
  - Y : Int32 [Plain]
  - MouseButton : Int32 [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.KeyPressArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Key : Int32 [Plain]
  - ScanCode : Int32 [Plain]
  - KeyAction : Int32 [Plain]
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.LocationChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Location : Drawing.Rectangle [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.MonitorClickEventArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Event : UiPath.Core.EventInfo [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]
  - Selector : String [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.MonitorKeyboardEventArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Event : UiPath.Core.EventInfo [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]
  - Selector : String [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.MouseClickedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - X : Int32 [Plain]
  - Y : Int32 [Plain]
  - MouseButton : Int32 [Plain]
  - IsMouseButtonPressed : Boolean [Plain]
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.SapWebPageMonitorArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ChangedAttributes : String[] [Plain]
  - ChangedAttributeValues : Object[] [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.SelectionChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Selection : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.StateChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - State : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TabActivatedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - TabId : String [Plain]
  - WindowId : String [Plain]
  - Title : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TabCreatedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - TabId : String [Plain]
  - WindowId : String [Plain]
  - Title : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TabDialogClosedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DialogConfirmed : Boolean [Plain]
  - UserInput : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TabDialogOpeningArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DialogMessage : String [Plain]
  - DialogType : String [Plain]
  - Url : String [Plain]
  - DefaultPrompt : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TabNavigationCompletedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Url : String [Plain]
  - TabId : Int32 [Plain]
  - FrameId : Int32 [Plain]
  - TimeStampMs : Double [Plain]
  - DateTime : DateTime [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TabNavigationStartedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Url : String [Plain]
  - TabId : Int32 [Plain]
  - FrameId : Int32 [Plain]
  - TimeStampMs : Double [Plain]
  - DateTime : DateTime [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TabRemovedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - TabId : String [Plain]
  - WindowId : String [Plain]
  - IsWindowClosing : Boolean [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TabUpdatedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - TabId : String [Plain]
  - WindowId : String [Plain]
  - Status : String [Plain]
  - Title : String [Plain]
  - Url : String [Plain]
  - Active : Boolean [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.TextChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Text : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.UiaTextRange
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Text : String [Plain]
  - BoundingRectangles : Drawing.Rectangle[] [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.UiaTextSelectionChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - TextRanges : UiPath.UIAutomationNext.Activities.Triggers.UiaTextRange[] [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.UiaToggledArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - State : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.UiElementTriggerArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebKeyPressArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Key : String [Plain]
  - Code : String [Plain]
  - AltKey : Boolean [Plain]
  - CtrlKey : Boolean [Plain]
  - ShiftKey : Boolean [Plain]
  - Location : Int32 [Plain]
  - IsComposing : Boolean [Plain]
  - MetaKey : Boolean [Plain]
  - Repeat : Boolean [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebMouseEventArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ScreenX : Int32 [Plain]
  - ScreenY : Int32 [Plain]
  - ClientX : Int32 [Plain]
  - ClientY : Int32 [Plain]
  - MovementX : Int32 [Plain]
  - MovementY : Int32 [Plain]
  - OffsetX : Int32 [Plain]
  - OffsetY : Int32 [Plain]
  - PageX : Int32 [Plain]
  - PageY : Int32 [Plain]
  - Button : Int32 [Plain]
  - AltKey : Boolean [Plain]
  - CtrlKey : Boolean [Plain]
  - ShiftKey : Boolean [Plain]
  - MetaKey : Boolean [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebRequestBeforeRedirectArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - RedirectUrl : String [Plain]
  - FromCache : Boolean [Plain]
  - Ip : String [Plain]
  - ResponseHeaders : String [Plain]
  - StatusCode : String [Plain]
  - StatusLine : String [Plain]
  - FrameId : String [Plain]
  - Initiator : String [Plain]
  - Method : String [Plain]
  - ParentFrameId : String [Plain]
  - RequestId : String [Plain]
  - TabId : String [Plain]
  - TimeStamp : String [Plain]
  - Type : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebRequestBeforeRequestArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - FrameId : String [Plain]
  - Initiator : String [Plain]
  - Method : String [Plain]
  - ParentFrameId : String [Plain]
  - RequestId : String [Plain]
  - TabId : String [Plain]
  - TimeStamp : String [Plain]
  - Type : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebRequestBeforeSendHeadersArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - RequestHeaders : String [Plain]
  - FrameId : String [Plain]
  - Initiator : String [Plain]
  - Method : String [Plain]
  - ParentFrameId : String [Plain]
  - RequestId : String [Plain]
  - TabId : String [Plain]
  - TimeStamp : String [Plain]
  - Type : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebRequestCompletedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - FromCache : Boolean [Plain]
  - Ip : String [Plain]
  - ResponseHeaders : String [Plain]
  - StatusCode : String [Plain]
  - StatusLine : String [Plain]
  - FrameId : String [Plain]
  - Initiator : String [Plain]
  - Method : String [Plain]
  - ParentFrameId : String [Plain]
  - RequestId : String [Plain]
  - TabId : String [Plain]
  - TimeStamp : String [Plain]
  - Type : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebRequestErrorOccurredArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Error : String [Plain]
  - FromCache : Boolean [Plain]
  - Ip : String [Plain]
  - FrameId : String [Plain]
  - Initiator : String [Plain]
  - Method : String [Plain]
  - ParentFrameId : String [Plain]
  - RequestId : String [Plain]
  - TabId : String [Plain]
  - TimeStamp : String [Plain]
  - Type : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebRequestHeadersReceivedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ResponseHeaders : String [Plain]
  - StatusCode : String [Plain]
  - StatusLine : String [Plain]
  - FrameId : String [Plain]
  - Initiator : String [Plain]
  - Method : String [Plain]
  - ParentFrameId : String [Plain]
  - RequestId : String [Plain]
  - TabId : String [Plain]
  - TimeStamp : String [Plain]
  - Type : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebRequestResponseStartedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - FromCache : Boolean [Plain]
  - Ip : String [Plain]
  - ResponseHeaders : String [Plain]
  - StatusCode : String [Plain]
  - StatusLine : String [Plain]
  - FrameId : String [Plain]
  - Initiator : String [Plain]
  - Method : String [Plain]
  - ParentFrameId : String [Plain]
  - RequestId : String [Plain]
  - TabId : String [Plain]
  - TimeStamp : String [Plain]
  - Type : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebRequestSendHeadersArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - RequestHeaders : String [Plain]
  - FrameId : String [Plain]
  - Initiator : String [Plain]
  - Method : String [Plain]
  - ParentFrameId : String [Plain]
  - RequestId : String [Plain]
  - TabId : String [Plain]
  - TimeStamp : String [Plain]
  - Type : String [Plain]
  - Url : String [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.Triggers.WebTextSelectionChangedArgs
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - SelectedText : String [Plain]
  - AnchorOffset : Int32 [Plain]
  - FocusOffset : Int32 [Plain]
  - AnchorClientBounds : Drawing.Rectangle [Plain]
  - FocusClientBounds : Drawing.Rectangle [Plain]
  - AnchorElement : UiPath.Core.UiElement [Plain]
  - FocusElement : UiPath.Core.UiElement [Plain]
  - SelectorIndex : Nullable<Int32> [Plain]
  - Selector : String [Plain]
  - TargetElement : UiPath.Core.UiElement [Plain]

## UiPath.UIAutomationNext.Activities.VerifyExecutionOptions
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - Mode : UiPath.UIAutomationNext.Enums.NVerifyMode [Plain]  // Verificar elemento
  - Retry : Boolean [In]  // Tentar novamente
  - Timeout : Double [In]  // Tempo Limite
  - DelayBefore : Double [In]  // Atraso antes
  - DisplayName : String [Plain]  // Nome de exibição
  - IsLoose : Boolean [Plain] = false

## UiPath.UIAutomationNext.Activities.VerifyExecutionTypeIntoOptions
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ExpectedText : String [In]  // Texto esperado
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Destino
  - Mode : UiPath.UIAutomationNext.Enums.NVerifyMode [Plain]  // Verificar elemento
  - Retry : Boolean [In]  // Tentar novamente
  - Timeout : Double [In]  // Tempo Limite
  - DelayBefore : Double [In]  // Atraso antes
  - DisplayName : String [Plain]  // Nome de exibição
  - IsLoose : Boolean [Plain] = false

## UiPath.UIAutomationNext.AnchorPresentationInfo
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Owner : UiPath.UIAutomationNext.Contracts.ITargetAnchorable [Plain]
  - AnchorIndex : Int32 [Plain]
  - FullSelectorArgument : String [In]  // Seletor restrito
  - FuzzySelectorArgument : String [In]  // Seletor difuso
  - NativeTextArgument : String [In]  // Texto nativo
  - NativeTextOccurrenceArgument : Int32 [In]  // Ocorrência de texto nativo
  - SearchSteps : UiPath.UIAutomationNext.Enums.TargetSearchSteps [Plain] = 0  // Métodos de segmentação
  - CvType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain] = 0  // Tipo de controle de CV
  - CvTextArgument : String [In]  // Texto do CV
  - CvTextOccurrenceArgument : Int32 [In]  // Ocorrência de texto CV
  - ImageOccurrenceArgument : Int32 [In]  // Ocorrência de Imagem
  - ImageAccuracyArgument : Double [In]  // Precisão da Imagem
  - SemanticTextArgument : String [In]
  - SemanticElementType : UiPath.UIAutomationNext.Enums.NSemanticElementType [Plain] = 0
  - IsLinkedToReadOnlyObjectRepository : Boolean [Plain]

## UiPath.UIAutomationNext.ClickOffset
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - OffsetPosition : UiPath.UIAutomationNext.Enums.NPosition [Plain] = 4  // Ponto de ancoragem
  - OffsetX : Int32 [In]  // Deslocamento de X
  - OffsetY : Int32 [In]  // Deslocamento de Y

## UiPath.UIAutomationNext.DialogHandling
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DismissAlerts : Boolean [In]  // Ignorar alertas
  - DismissConfirms : Boolean [In]  // Ignorar Confirmações
  - DismissPrompts : Boolean [In]  // Ignorar Prompts
  - ConfirmDialogResponse : UiPath.UIAutomationNext.Enums.NBrowserDialogResponse [In]  // Confirmar resposta da caixa de diálogo
  - PromptDialogResponse : UiPath.UIAutomationNext.Enums.NBrowserDialogResponse [In]  // Solicitar resposta da caixa de diálogo
  - PromptDialogResponseText : String [In]  // Texto de resposta do prompt

## UiPath.UIAutomationNext.Enums.AttachToActiveTabMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.BrowserCommunicationMethod
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.BrowserUserDataFolderMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.CursorMotionType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.ExtensionType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.GetTextMethod
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NActivityVersion
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NAppAttachMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NAppCloseMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NApplicationCardVersion
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NAppOpenMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NBlockInputType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NBrowserDialogResponse
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NBrowserDialogScopeType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NBrowserFilePickerScopeMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NBrowserType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NCheckStateMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NCheckType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NChildInteractionMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NClickMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NClickType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NDateSelectionType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NDriverWebFramework
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NElementVisibility
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NEmptyFieldMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NExecutionWorld
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NFileNameMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NGoToUrlMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NHealingAgentBehavior
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NInteractionMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NKeyModifiers
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NMouseButton
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NMultiLogonOption
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NNavigateBrowserAction
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NPopupHandleState
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NPosition
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NPositioningMatchType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NSAPSupportedFramework
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NSAPTableCellScopeRowType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NSAPVKey
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NSaveScreenshotTo
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NScrapingMethod
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NScrapingOptions
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NScrollDirection
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NScrollType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NSemanticElementType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NTargetAppVersion
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NTargetVersion
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NTypeByClipboardMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NUICoreColor
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NUITaskAgentType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NVerifyMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NVisibilityLevel
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NWaitForReady
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NWebDriverMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NWindowOperationType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.NWindowResize
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.SelectionActivityType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.SelectorStrategy
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.TargetSearchSteps
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.TargetType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.UIElementType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Enums.VariableType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.ExtractMetadataObjectReference
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Value : String [Plain]

## UiPath.UIAutomationNext.Models.BaseModel
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Models.CreateApplicationOptions
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - WithIcon : Boolean [Plain]
  - WithScreenshot : Boolean [Plain]

## UiPath.UIAutomationNext.Models.GenerationOptions
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Prompt : String [Plain]
  - Url : String [Plain]
  - ExpectedInputs : Collections.Generic.List<String> [Plain]
  - ExpectedOutputs : Collections.Generic.List<String> [Plain]

## UiPath.UIAutomationNext.Models.ImageColorData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Empty : UiPath.UIAutomationNext.Models.ImageColorData [Plain]
  - ImageBase64 : String [Plain]
  - Pixels : UiPath.UIAutomationNext.Models.PixelImageData[] [Plain]
  - Width : Int32 [Plain]
  - Height : Int32 [Plain]
  - OffsetPoint : Nullable<Drawing.Point> [Plain]
  - CenterColor : UiPath.UIAutomationNext.Models.PixelImageData [Plain]
  - OffsetPointColor : UiPath.UIAutomationNext.Models.PixelImageData [Plain]
  - DominantColor : Drawing.Color [Plain]
  - DominantUICoreColor : UiPath.UIAutomationNext.Enums.NUICoreColor [Plain]
  - DominantKnownColor : Drawing.KnownColor [Plain]

## UiPath.UIAutomationNext.Models.ObjectRepositoryDesignData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Items : Collections.Generic.List<String> [Plain]
  - NativeEvents : String [Plain]

## UiPath.UIAutomationNext.Models.OperationContextParameters
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Consumer : String [Plain]
  - SessionId : String [Plain]
  - JobId : String [Plain]
  - ProcessName : String [Plain]
  - FolderId : String [Plain]
  - TargetFramework : String [Plain]
  - InitiatedBy : String [Plain]
  - Default : UiPath.UIAutomationNext.Models.OperationContextParameters [Plain]

## UiPath.UIAutomationNext.Models.PixelImageData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - X : Int32 [Plain]
  - Y : Int32 [Plain]
  - Value : Int32 [Plain]
  - R : Byte [Plain]
  - G : Byte [Plain]
  - B : Byte [Plain]
  - RawColor : Drawing.Color [Plain]
  - Color : Drawing.Color [Plain]
  - CoreColor : UiPath.UIAutomationNext.Enums.NUICoreColor [Plain]
  - KnownColor : Drawing.KnownColor [Plain]

## UiPath.UIAutomationNext.Models.RuntimeVariable
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Name : String [Plain]
  - RawValue : String [Plain]
  - Value : String [Plain]
  - IsSecure : Boolean [Plain]

## UiPath.UIAutomationNext.Models.SpecialKey
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Models.StudioContext
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Application : String [Plain]
  - Title : String [Plain]

## UiPath.UIAutomationNext.Models.UICoreColorFrequency
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Color : UiPath.UIAutomationNext.Enums.NUICoreColor [Plain]
  - Count : Int32 [Plain]

## UiPath.UIAutomationNext.Models.XString
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - IsSecure : Boolean [Plain]
  - PlainText : String [Plain]
  - Secure : Security.SecureString [Plain]

## UiPath.UIAutomationNext.ObjectRepositoryScreenData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - TargetApp : UiPath.UIAutomationNext.TargetApp [Plain]
  - Data : Collections.Generic.Dictionary<String,Object> [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Variables : Collections.Generic.List<UiPath.UIAutomationNext.ObjectRepositoryVariableData> [Plain]

## UiPath.UIAutomationNext.ObjectRepositoryTargetData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - TargetAnchorable : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - DesignData : UiPath.UIAutomationNext.Models.ObjectRepositoryDesignData [Plain]
  - Data : Collections.Generic.Dictionary<String,Object> [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Variables : Collections.Generic.List<UiPath.UIAutomationNext.ObjectRepositoryVariableData> [Plain]

## UiPath.UIAutomationNext.ObjectRepositoryVariableData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Name : String [Plain]
  - IsVariable : Boolean [Plain] = true
  - IsString : Boolean [Plain] = true
  - DefaultValue : Object [Plain]

## UiPath.UIAutomationNext.PointOffset
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Position : UiPath.UIAutomationNext.Enums.NPosition [Plain] = 4  // Ponto de ancoragem
  - X : Int32 [In]  // Deslocamento de X
  - Y : Int32 [In]  // Deslocamento de Y

## UiPath.UIAutomationNext.RegionOffset
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Position : UiPath.UIAutomationNext.Enums.NPosition [Plain] = 0  // Ponto de ancoragem
  - X : Int32 [In]  // Deslocamento de X
  - Y : Int32 [In]  // Deslocamento de Y
  - Width : Int32 [In]  // Largura do deslocamento
  - Height : Int32 [In]  // Altura do deslocamento
  - Area : Drawing.Rectangle [Plain]
  - IsAreaResolved : Boolean [Plain]

## UiPath.UIAutomationNext.ScopeIdentity
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - ScopeIdentifierPropertyName : String [Plain]
  - InScopePropertyName : String [Plain]

## UiPath.UIAutomationNext.Target
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - FullSelectorArgument : String [In]  // Seletor restrito
  - FuzzySelectorArgument : String [In]  // Seletor difuso
  - SearchSteps : UiPath.UIAutomationNext.Enums.TargetSearchSteps [Plain] = 0  // Métodos de segmentação
  - TargetType : UiPath.UIAutomationNext.Enums.TargetType [Plain] = 0
  - OwnerTarget : UiPath.UIAutomationNext.Contracts.ITargetAnchorable [Plain]
  - ScopeSelector : String [Plain]
  - PartialSelector : String [Plain]
  - FuzzyPartialSelector : String [Plain]
  - FullSelector : String [Plain]
  - FuzzySelector : String [Plain]
  - FuzzyAccuracy : Double [Plain] = 0.5
  - FuzzyMatches : Int32 [Plain] = 100
  - ImageBase64 : String [Plain]
  - ImageOccurrenceArgument : Int32 [In]  // Ocorrência de Imagem
  - ImageOccurrence : Int32 [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - Text : String [Plain]
  - NativeTextArgument : String [In]  // Texto nativo
  - NativeText : String [Plain]
  - NativeTextOccurrenceArgument : Int32 [In]  // Ocorrência de texto nativo
  - NativeTextOccurrence : Int32 [Plain]
  - IsNativeTextCaseSensitive : Boolean [Plain] = false
  - TextMethod : UiPath.UIAutomationNext.Enums.GetTextMethod [Plain] = 0
  - TextSelector : String [Plain]
  - OCRText : String [Plain]
  - OCRAccuracy : Double [Plain] = 0.7
  - ElementType : UiPath.UIAutomationNext.Enums.UIElementType [Plain] = 0
  - Accuracy : Double [Plain] = 0.8
  - ImageAccuracyArgument : Double [In]  // Precisão da Imagem
  - ImageAccuracy : Double [Plain]
  - SemanticElementType : UiPath.UIAutomationNext.Enums.NSemanticElementType [Plain] = 0
  - SemanticTextArgument : String [In]
  - SemanticTexts : String[] [Plain]
  - CvType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain] = 0  // Tipo de controle de CV
  - CvDescription : String [Plain]
  - CVScreenId : String [Plain]
  - CvColumns : Collections.Generic.IEnumerable<String> [Plain]
  - CvTextArgument : String [In]  // Texto do CV
  - CvText : String [Plain]
  - CvTextOccurrenceArgument : Int32 [In]  // Ocorrência de texto CV
  - CvTextOccurrence : Int32 [Plain]
  - CvElementArea : Nullable<Drawing.Rectangle> [Plain]
  - CvTextArea : Nullable<Drawing.Rectangle> [Plain]
  - Guid : String [Plain]
  - FriendlyName : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - IsLinkedToReadOnlyObjectRepository : Boolean [Plain]

## UiPath.UIAutomationNext.TargetAnchorable
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Anchors : Collections.Generic.IEnumerable<UiPath.UIAutomationNext.Contracts.ITarget> [Plain]
  - AnchorCount : Int32 [Plain]
  - PointOffset : UiPath.UIAutomationNext.PointOffset [Plain]  // Deslocamento de clique
  - RegionOffset : UiPath.UIAutomationNext.RegionOffset [Plain]  // Área
  - PointOffsetPresentation : UiPath.UIAutomationNext.PointOffset [Plain]  // Deslocamento de clique
  - TelemetryData : Collections.Generic.Dictionary<String,String> [Plain]
  - CheckVisibility : Boolean [Plain]
  - Visibility : UiPath.UIAutomationNext.Enums.NElementVisibility [Plain]
  - ElementVisibilityArgument : UiPath.UIAutomationNext.Enums.NElementVisibility [In]  // Verificação de visibilidade
  - ElementVisibility : UiPath.UIAutomationNext.Enums.NElementVisibility [Plain]
  - IsResponsive : Boolean [Plain] = false  // Sites responsivos
  - InformativeScreenshot : String [Plain]
  - ScopeSelectorArgument : String [In]  // Seletor de janela (instância do Aplicativo)
  - ScopeSelector : String [Plain]
  - WaitForReadyArgument : UiPath.UIAutomationNext.Enums.NWaitForReady [In]  // Aguardar carregamento da página
  - WaitForReady : UiPath.UIAutomationNext.Enums.NWaitForReady [Plain]
  - SemanticSelectorArgument : String [In]  // Seletor semântico
  - SemanticSelector : String [Plain]
  - BrowserURL : String [Plain]
  - SelectionStrategy : UiPath.UIAutomationNext.Enums.SelectorStrategy [Plain] = 0
  - PositioningType : UiPath.UIAutomationNext.Enums.NPositioningMatchType [Plain] = 0
  - DesignTimeScaleFactor : Double [Plain] = 0
  - DataCollectionScreenshotId : String [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NTargetVersion [Plain] = 0
  - Anchor0 : UiPath.UIAutomationNext.AnchorPresentationInfo [Plain]  // Âncora 1
  - Anchor1 : UiPath.UIAutomationNext.AnchorPresentationInfo [Plain]  // Âncora 2
  - Anchor2 : UiPath.UIAutomationNext.AnchorPresentationInfo [Plain]  // Âncora 3
  - Anchor3 : UiPath.UIAutomationNext.AnchorPresentationInfo [Plain]  // Âncora 4
  - OwnerTarget : UiPath.UIAutomationNext.Contracts.ITargetAnchorable [Plain]
  - FullSelectorArgument : String [In]  // Seletor restrito
  - FuzzySelectorArgument : String [In]  // Seletor difuso
  - SearchSteps : UiPath.UIAutomationNext.Enums.TargetSearchSteps [Plain] = 0  // Métodos de segmentação
  - TargetType : UiPath.UIAutomationNext.Enums.TargetType [Plain] = 0
  - PartialSelector : String [Plain]
  - FuzzyPartialSelector : String [Plain]
  - FullSelector : String [Plain]
  - FuzzySelector : String [Plain]
  - FuzzyAccuracy : Double [Plain] = 0.5
  - FuzzyMatches : Int32 [Plain] = 100
  - ImageBase64 : String [Plain]
  - ImageOccurrenceArgument : Int32 [In]  // Ocorrência de Imagem
  - ImageOccurrence : Int32 [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - Text : String [Plain]
  - NativeTextArgument : String [In]  // Texto nativo
  - NativeText : String [Plain]
  - NativeTextOccurrenceArgument : Int32 [In]  // Ocorrência de texto nativo
  - NativeTextOccurrence : Int32 [Plain]
  - IsNativeTextCaseSensitive : Boolean [Plain] = false
  - TextMethod : UiPath.UIAutomationNext.Enums.GetTextMethod [Plain] = 0
  - TextSelector : String [Plain]
  - OCRText : String [Plain]
  - OCRAccuracy : Double [Plain] = 0.7
  - ElementType : UiPath.UIAutomationNext.Enums.UIElementType [Plain] = 0
  - Accuracy : Double [Plain] = 0.8
  - ImageAccuracyArgument : Double [In]  // Precisão da Imagem
  - ImageAccuracy : Double [Plain]
  - SemanticElementType : UiPath.UIAutomationNext.Enums.NSemanticElementType [Plain] = 0
  - SemanticTextArgument : String [In]
  - SemanticTexts : String[] [Plain]
  - CvType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain] = 0  // Tipo de controle de CV
  - CvDescription : String [Plain]
  - CVScreenId : String [Plain]
  - CvColumns : Collections.Generic.IEnumerable<String> [Plain]
  - CvTextArgument : String [In]  // Texto do CV
  - CvText : String [Plain]
  - CvTextOccurrenceArgument : Int32 [In]  // Ocorrência de texto CV
  - CvTextOccurrence : Int32 [Plain]
  - CvElementArea : Nullable<Drawing.Rectangle> [Plain]
  - CvTextArea : Nullable<Drawing.Rectangle> [Plain]
  - Guid : String [Plain]
  - FriendlyName : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - IsLinkedToReadOnlyObjectRepository : Boolean [Plain]

## UiPath.UIAutomationNext.TargetApp
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Selector : String [In]  // Seletor
  - FilePath : String [In]  // Caminho do arquivo
  - Arguments : String [In]  // Argumentos
  - Url : String [In]  // URL
  - BrowserType : UiPath.UIAutomationNext.Enums.NBrowserType [Plain] = -1  // Tipo de navegador
  - WorkingDirectory : String [In]  // DiretórioDeTrabalho
  - InformativeScreenshot : String [Plain]
  - IconBase64 : String [Plain]
  - IsExactTitleEnabled : Boolean [Plain] = false
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Area : Drawing.Rectangle [Plain]
  - Title : String [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NTargetAppVersion [Plain] = 0

## UiPath.UIAutomationNext.Triggers.NClickTriggerMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Triggers.NKeyTriggerMode
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Triggers.NNativeEventType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.UserDataConnection
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Id : String [Plain]
  - Name : String [Plain]

