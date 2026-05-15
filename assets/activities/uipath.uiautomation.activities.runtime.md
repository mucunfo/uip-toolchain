# uipath.uiautomation.activities.runtime
Assembly: UiPath.CV.Activities v25.10.27.0
PackageVersion: 25.10.27
ActivityCount: 341

## UiPath.Core.Activities.Activate
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ActiveXInvalidArgumentsException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ActiveXOutputArgumentsNotSupportedException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ActiveXUnknownMethodException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ActivityTimeoutException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.Anchor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Element : UiPath.Core.UiElement [Plain]
  - Position : UiPath.Core.AnchorPosition [Plain]

## UiPath.Core.Activities.Anchor2Data
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Container : UiPath.Core.UiElement [Plain]

## UiPath.Core.Activities.AnchorBase
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **AnchorProvider** : Activities.Activity<UiPath.Core.UiElement> [Plain]
- optional:
  - Action : Activities.ActivityAction<UiPath.Core.Activities.Anchor> [Plain]
  - AnchorPosition : UiPath.Core.AnchorPosition [In]  // Anchor position
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.AnchorContextAware
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **AnchorProvider** : Activities.ActivityAction<UiPath.Core.Activities.Anchor2Data> [Plain]
  - **TargetProvider** : Activities.ActivityAction<UiPath.Core.Activities.Anchor2Data> [Plain]
  - **DesignAnchor** : Drawing.Rectangle [In]  // Anchor bounding box
  - **DesignTarget** : Drawing.Rectangle [In]  // Target bounding box
- optional:
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.AppLog
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Instance : UiPath.Core.Activities.AppLog [Plain]

## UiPath.Core.Activities.AutomateActiveXException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.BlockUserInput
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Keys** : String [Plain]  // Key
- optional:
  - Body : Activities.Activity [Plain]
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - BlockType : UiPath.Core.BlockMethod [In] = 0  // Block method
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In] = 1  // Key modifiers
  - SpecialKey : Boolean [In] = true  // Special key
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.BrowserNotSetException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.BrowserScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Selector : String [In]  // Selector
  - BrowserType : UiPath.Core.BrowserType [In]  // Browser type
  - SearchScope : UiPath.Core.Browser [In]  // Search scope
  - Browser : UiPath.Core.Browser [In]  // Browser
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - UiBrowser : UiPath.Core.Browser [Out]  // Ui browser
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - InformativeScreenshot : String [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Callout
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Title** : String [In]  // Title
  - **Content** : String [In]  // Content
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - Timer : Int32 [In]  // Timer
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CalloutScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - RefreshInterval : TimeSpan [In]  // Refresh interval
  - CalloutForm : Activities.ActivityFunc`3<Drawing.Rectangle,IntPtr,Threading.Tasks.Task> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CellScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - RowOptions : Collections.Generic.List<String> [Plain]
  - NotSupportedMessage : String [Plain]
  - ColumnName : String [In]  // Column name
  - RowNumber : String [In]  // Row number
  - TableRow : Int32 [Out]  // Table row index
  - ColumnNames : Collections.Generic.List<String> [Plain]
  - UiElement : UiPath.Core.UiElement [Out]  // Ui element
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - Body : Activities.ActivityAction<Object> [Plain]
  - InformativeScreenshot : String [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CellScopeException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.Check
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Action : UiPath.Core.Activities.CheckType [In]  // Ação
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayAfter : Int32 [In]  // AtrasoApós
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CheckType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.Click
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - SimulateClick : Boolean [In]  // Simulate click
  - SendWindowMessages : Boolean [In]  // Send window messages
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // TipoDeMovimentoDoCursor
  - ClickType : UiPath.Core.ClickType [In]  // TipoDeClique
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - UnblockInput : Boolean [In]  // Unblock input
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ClickImage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - SendWindowMessages : Boolean [In]  // Send window messages
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - ClickType : UiPath.Core.ClickType [In]  // TipoDeClique
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ClickImageTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  // Selector
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - ClippingRegion : UiPath.Core.Region [Plain]  // Clipping region
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - EventType : UiPath.Core.EventType [In]  // Event type
  - BlockEvent : Boolean [In] = false  // Block event
  - TriggerMode : UiPath.Core.TriggerMode [In]  // Trigger mode
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ClickImageTriggerV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  // Selector
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - ClippingRegion : UiPath.Core.Region [Plain]  // Clipping region
  - TriggerMode : UiPath.Core.TriggerMode [In]  // Trigger mode
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - BlockEvent : Boolean [In]  // Block event
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]

## UiPath.Core.Activities.ClickOCRText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Occurrence** : Int32 [In]  // Occurrence
- optional:
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - ClickType : UiPath.Core.ClickType [In]  // TipoDeClique
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - SendWindowMessages : Boolean [In]  // Send window messages
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ClickText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Occurrence** : Int32 [In]  // Occurrence
- optional:
  - SendWindowMessages : Boolean [In]  // Send window messages
  - FormattedText : Boolean [In]  // Formatted text
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - ClickType : UiPath.Core.ClickType [In]  // TipoDeClique
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ClickTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  // Selector
- optional:
  - IncludeChildren : Boolean [In]  // Include children
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - ClippingRegion : UiPath.Core.Region [Plain]  // Clipping region
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - EventType : UiPath.Core.EventType [In]  // Event type
  - BlockEvent : Boolean [In] = false  // Block event
  - TriggerMode : UiPath.Core.TriggerMode [In]  // Trigger mode
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ClickTriggerV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  // Selector
- optional:
  - IncludeChildren : Boolean [In]  // Include children
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - ClippingRegion : UiPath.Core.Region [Plain]  // Clipping region
  - TriggerMode : UiPath.Core.TriggerMode [In]  // Trigger mode
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - BlockEvent : Boolean [In]  // Block event
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]

## UiPath.Core.Activities.ClipboardWrapper
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - OriginalContent : String [Plain]

## UiPath.Core.Activities.CloseApplication
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CloseTab
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Browser : UiPath.Core.Browser [In]  @group=Browser  // Browser
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CloseWindow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  @group=Find Window  // Selector
- optional:
  - UseWindow : UiPath.Core.Window [In]  @group=Use Window  // Use window
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - WaitForReady : UiPath.Core.WaitForReady [In]  // Wait for ready
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CopySelectedText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - SendWindowMessages : Boolean [In]  // Send window messages
  - Result : ? [Out]  // Result
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.CursorPosition
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - OffsetX : Int32 [In]  // Offset x
  - OffsetY : Int32 [In]  // Offset y
  - Position : UiPath.Core.Position [Plain]  // Position

## UiPath.Core.Activities.ElementAttributeChangeTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **AttributeName** : String [In]  // Attribute
  - **Selector** : String [In]  // Selector
- optional:
  - VisibilityType : UiPath.Core.Activities.ElementVisibilityType [In]  // Element visibility type
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]

## UiPath.Core.Activities.ElementNotSetException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ElementScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UiElement : UiPath.Core.UiElement [Out]  // Ui element
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - Body : Activities.ActivityAction<Object> [Plain]
  - InformativeScreenshot : String [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ElementStateChangeTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  // Selector
- optional:
  - ElementStateChangeType : UiPath.Core.Activities.StateChangedEvent [In]  // Element state change type
  - VisibilityType : UiPath.Core.Activities.ElementVisibilityType [In]  // Element visibility type
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]

## UiPath.Core.Activities.ElementVisibilityType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.EventInfoTriggerArgs
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - EventInfo : UiPath.Core.EventInfo [Plain]

## UiPath.Core.Activities.ExpandALVTreeException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ExportUiTree
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - Filter : String [In]  // Filter
  - UiFramework : UiPath.Core.Activities.UiTree.SelectorStrategy [Plain]  // Ui framework
  - DestinationFile : String [In]  // Destination file
  - Format : UiPath.Core.Activities.UiTree.ExportFormat [Plain]  // Export format
  - OperationTimeoutMS : Nullable<Int32> [In]  // Operation timeout ms
  - IncludeScreenshots : Boolean [Plain]  // Include screenshots
  - Overwrite : Boolean [Plain]  // Overwrite
  - Priority : UiPath.Core.Activities.UiTree.Priority [Plain]  // Priority
  - ExportedString : String [Out]  // Exported string
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ExtractData
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ExtractMetadata** : String [In]  // Extract metadata
  - **DataTable** : Data.DataTable [InOut]  // Data table
- optional:
  - MaxNumberOfResults : Int32 [In]  // Max number of results
  - NextLinkSelector : String [In]  // Next link selector
  - SimulateClick : Boolean [In] = true  // Simulate click
  - SendWindowMessages : Boolean [In]  // Send window messages
  - DelayBetweenPagesMS : Int32 [In]  // Delay between pages ms
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.FindChildren
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Filter** : String [In]  // Filter
- optional:
  - Scope : UiPath.Core.FindScope [In]  // Scope
  - Children : Collections.Generic.IEnumerable<UiPath.Core.UiElement> [Out]  // Children
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.FindImageMatches
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - Matches : Collections.Generic.IEnumerable<UiPath.Core.UiElement> [Out]  // Matches
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.FindOCRText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Occurrence** : Int32 [In]  // Occurrence
- optional:
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - Version : UiPath.Core.ActivityVersion [Plain] = 0
  - Element : UiPath.Core.UiElement [Out]  // Elemento
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.FindRelative
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - RelativeElement : UiPath.Core.UiElement [Out]  // Relative element
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.FindText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Occurrence** : Int32 [In]  // Occurrence
- optional:
  - UiElement : UiPath.Core.UiElement [Out]  // Ui element
  - FormattedText : Boolean [In]  // Formatted text
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetActiveWindow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ApplicationWindow : UiPath.Core.Window [Out]  // Application window
  - Body : Activities.ActivityAction<Object> [Plain]
  - InformativeScreenshot : String [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetAncestor
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UpLevels : Int32 [Plain]  // Up levels
  - Ancestor : UiPath.Core.UiElement [Out]  // Ancestor
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Attribute** : String [In]  // Attribute
- optional:
  - Result : ? [Out]  // Result
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetElementActivity
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UiElement : UiPath.Core.UiElement [Out]  // Ui element
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - OwnerActivityDisplayName : String [Plain]
  - OwnerActivityType : Type [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetEventInfo`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - InterceptedEvent : Object [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetFromClipboard
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Result : ? [Out]  // Result
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetFullText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Text : ? [Out]  // Texto
  - IgnoreHidden : Boolean [In]  // Ignore hidden
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetOCRText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Text : ? [Out]  // Texto
  - WordsInfo : Collections.Generic.IEnumerable<UiPath.Core.TextInfo> [Out]  // Words info
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetPassword
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Password : String [Plain]  // Password
  - ProtectedPassword : String [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetPosition
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Rectangle : Drawing.Rectangle [Out]  // Rectangle
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetSourceElement
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - InterceptedEvent : Object [In]
  - UiElement : UiPath.Core.UiElement [Out]  // Ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetSourceElementV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **EventInfo** : UiPath.Core.EventInfo [In]  // Event info
- optional:
  - UiElement : UiPath.Core.UiElement [Out]  // Ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetValue
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Value : ? [Out]  // Value
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GetVisibleText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Text : ? [Out]  // Texto
  - WordsInfo : Collections.Generic.IEnumerable<UiPath.Core.TextInfo> [Out]  // Words info
  - Separators : String [In]  // Separators
  - FormattedText : Boolean [In]  // Formatted text
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GoBack
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Browser : UiPath.Core.Browser [In]  @group=Browser  // Browser
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GoForward
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Browser : UiPath.Core.Browser [In]  @group=Browser  // Browser
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GoHome
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Browser : UiPath.Core.Browser [In]  @group=Browser  // Browser
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.GoogleCloudOCR
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Image** : Drawing.Image [In]  // Imagem 
- optional:
  - ApiKey : String [In]  // Api key
  - DetectionMode : UiPath.Vision.Core.OCR.GoogleCloudDetectionMode [Plain]  // Detection mode
  - Region : UiPath.Vision.Core.OCR.GoogleCloudRegion [In]  // Google cloud region
  - ResizeToApiLimits : Boolean [Plain]  // Resize to max limit if necessary
  - Language : String [In]  // Language
  - Scale : Double [In]  // Scale
  - Text : String [Out]  // Texto
  - ComputeSkewAngle : Boolean [Plain]
  - ExtractWords : Boolean [Plain]  // Extract words
  - FilterRegion : UiPath.Core.Region [Plain]  // Filter region
  - Profile : UiPath.Vision.OCR.OCRProfile [In]  // Profile
  - Languages : String[] [Plain]
  - NoopExecution : Boolean [Plain]

## UiPath.Core.Activities.GoogleOCR
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Image** : Drawing.Image [In]  // Imagem 
- optional:
  - AllowedCharacters : String [In]  // Allowed characters
  - DeniedCharacters : String [In]  // Denied characters
  - Invert : Boolean [In]  // Invert
  - Profile : UiPath.Vision.OCR.OCRProfile [In]  // Profile
  - Language : String [In]  // Language
  - Scale : Double [In]  // Scale
  - Text : String [Out]  // Texto
  - ComputeSkewAngle : Boolean [Plain]
  - ExtractWords : Boolean [Plain]  // Extract words
  - FilterRegion : UiPath.Core.Region [Plain]  // Filter region
  - Languages : String[] [Plain]
  - NoopExecution : Boolean [Plain]

## UiPath.Core.Activities.HideWindow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Window : UiPath.Core.Window [In]  @group=Use Window  // Window
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Highlight
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - HighlightTime : Int32 [In]  // Highlight time
  - Color : Drawing.Color [Plain]  // Color
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.HotkeyTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Key** : String [Plain]  // Key
- optional:
  - EventMode : UiPath.Core.EventMode [In]  // Event mode
  - KeyModifiers : UiPath.Core.Activities.MonitoringKeyModifiers [In]  // Key modifiers
  - UseWindowsHotKey : Boolean [Plain]  // Use windows hot key
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.HotkeyTriggerV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Key** : String [In]  // Key
- optional:
  - BlockEvent : Boolean [In]  // Block event
  - KeyModifiers : UiPath.Core.Activities.MonitoringKeyModifiers [In]  // Key modifiers
  - UseWindowsHotKey : Boolean [Plain]  // Use windows hot key

## UiPath.Core.Activities.Hover
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - SimulateHover : Boolean [In]  // Simulate hover
  - SendWindowMessages : Boolean [In]  // Send window messages
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // TipoDeMovimentoDoCursor
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.HoverImage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - SendWindowMessages : Boolean [In]  // Send window messages
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.HoverOCRText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Occurrence** : Int32 [In]  // Occurrence
- optional:
  - SendWindowMessages : Boolean [In]  // Send window messages
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.HoverText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Occurrence** : Int32 [In]  // Occurrence
- optional:
  - SendWindowMessages : Boolean [In]  // Send window messages
  - FormattedText : Boolean [In]  // Formatted text
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ImageFindCriteria
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FindProfile : UiPath.Core.Activities.ImageFindProfile [Plain]
  - InitialScalingFactor : Double [Plain]
  - ScalingDelta : Double [Plain]
  - Image : UiPath.Core.Image [Plain]
  - Accuracy : Double [Plain]

## UiPath.Core.Activities.ImageFindProfile
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ImageFound
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - Found : Boolean [Out]  // Found
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ImageTarget
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Image : UiPath.Core.Image [In]  // Imagem 
  - Accuracy : Double [In]  // Precisão
  - TargetImageBase64 : String [Plain]
  - Profile : UiPath.Core.Activities.ImageFindProfile [In] = 0  // Profile
  - InitialScalingFactor : Double [Plain] = 1
  - Reference : String [Plain]
  - ContentHash : String [Plain]

## UiPath.Core.Activities.IndicateOnScreen
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - SelectScreenRegion : Boolean [In]  // Select screen region
  - HidePreview : Boolean [In]  // Hide preview
  - SelectedUiElement : UiPath.Core.UiElement [Out]  // Selected ui element
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.InjectDotNetAmbiguousMethodException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InjectDotNetArgumentNotDefinedException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InjectDotNetAssemblyReflectionException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InjectDotNetCode
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **AssemblyPath** : String [In]  // Assembly
  - **TypeName** : String [In]  // Type
  - **MethodName** : String [In]  // Method
- optional:
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Arguments
  - PassUIControlAsFirstArgument : Boolean [In]  // Pass ui control as first argument
  - Result : Object [Out]  // Result
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.InjectDotNetCodeResult
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InjectDotNetMethodNotFoundException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InjectDotNetTypeNotFoundException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InjectDotNetTypeNotSupportedException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InjectJsScript
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ScriptCode** : String [In]  // Script code
- optional:
  - InputParameter : String [In]  // Input parameter
  - ScriptOutput : ? [Out]  // Script output
  - ExecutionWorld : UiPath.UIAutomationNext.Enums.NExecutionWorld [In]  // Execution world
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Input
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.InvokeActiveX
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MethodName** : String [In]  // Method
- optional:
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Arguments
  - Result : Object [Out]  // Result
  - MethodItems : Collections.Generic.List<String> [Plain]
  - InvokeType : String [Plain]
  - ActiveXTypeInfo : String [Plain]
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.KeyModifiers
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.KeyPressTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  // Selector
- optional:
  - Key : String [In]  // Key
  - IncludeChildren : Boolean [In]  // Include children
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - EventType : UiPath.Core.EventType [In]  // Event type
  - BlockEvent : Boolean [In] = false  // Block event
  - TriggerMode : UiPath.Core.TriggerMode [In]  // Trigger mode
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.KeyPressTriggerV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  // Selector
- optional:
  - Key : String [In]  // Key
  - IncludeChildren : Boolean [In]  // Include children
  - TriggerMode : UiPath.Core.TriggerMode [In]  // Trigger mode
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - BlockEvent : Boolean [In]  // Block event
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]

## UiPath.Core.Activities.LoadImage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // File
- optional:
  - Image : UiPath.Core.Image [Out]  // Imagem 
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
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

## UiPath.Core.Activities.MaximizeWindow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Window : UiPath.Core.Window [In]  @group=Use Window  // Window
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.MicrosoftAzureComputerVisionOCR
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Image** : Drawing.Image [In]  // Imagem 
- optional:
  - ApiKey : String [In]  // Api key
  - Endpoint : String [In]  // Endpoint
  - Language : String [In]  // Language
  - HandwritingRecognition : Boolean [Plain]  // Use read api
  - Scale : Double [In]  // Scale
  - Text : String [Out]  // Texto
  - ComputeSkewAngle : Boolean [Plain]
  - ExtractWords : Boolean [Plain]  // Extract words
  - FilterRegion : UiPath.Core.Region [Plain]  // Filter region
  - Profile : UiPath.Vision.OCR.OCRProfile [In]  // Profile
  - Languages : String[] [Plain]
  - NoopExecution : Boolean [Plain]

## UiPath.Core.Activities.MicrosoftCloudOCR
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ApiKey** : String [In]  // Api key
  - **Image** : Drawing.Image [In]  // Imagem 
- optional:
  - Language : String [In]  // Language
  - Scale : Double [In]  // Scale
  - Text : String [Out]  // Texto
  - ComputeSkewAngle : Boolean [Plain]
  - ExtractWords : Boolean [Plain]  // Extract words
  - FilterRegion : UiPath.Core.Region [Plain]  // Filter region
  - Profile : UiPath.Vision.OCR.OCRProfile [In]  // Profile
  - Languages : String[] [Plain]
  - NoopExecution : Boolean [Plain]

## UiPath.Core.Activities.MicrosoftOCR
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Image** : Drawing.Image [In]  // Imagem 
- optional:
  - Language : String [In]  // Language
  - Profile : UiPath.Vision.OCR.OCRProfile [In]  // Profile
  - Scale : Double [In]  // Scale
  - Text : String [Out]  // Texto
  - ComputeSkewAngle : Boolean [Plain]
  - ExtractWords : Boolean [Plain]  // Extract words
  - FilterRegion : UiPath.Core.Region [Plain]  // Filter region
  - Languages : String[] [Plain]
  - NoopExecution : Boolean [Plain]

## UiPath.Core.Activities.MinimizeWindow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Window : UiPath.Core.Window [In]  @group=Use Window  // Window
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.MonitorEvents
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - RepeatForever : Activities.Activity<Boolean> [Plain]  // Repeat forever
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Handler : Activities.ActivityAction<Object> [Plain]
  - Triggers : Collections.Generic.List<Activities.Activity> [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.MonitoringKeyModifiers
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.MouseTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - EventMode : UiPath.Core.EventMode [In]  // Event mode
  - KeyModifiers : UiPath.Core.Activities.MonitoringKeyModifiers [In]  // Key modifiers
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.MouseTriggerV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - BlockEvent : Boolean [In]  // Block event
  - KeyModifiers : UiPath.Core.Activities.MonitoringKeyModifiers [In]  // Key modifiers

## UiPath.Core.Activities.MoveWindow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - X : Int32 [In]  // X
  - Y : Int32 [In]  // Y
  - Width : Int32 [In]  // Width
  - Height : Int32 [In]  // Height
  - Window : UiPath.Core.Window [In]  @group=Use Window  // Window
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.NavigateTo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Url** : String [In]  // Url
- optional:
  - Browser : UiPath.Core.Browser [In]  @group=Browser  // Browser
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OCRTextExists
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Occurrence** : Int32 [In]  // Occurrence
- optional:
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OnImageAppear
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FoundElement : UiPath.Core.UiElement [Out]  // Found element
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Body : Activities.Activity [Plain]
  - RepeatForever : Activities.Activity<Boolean> [Plain]  // Repeat forever
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OnImageVanish
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Body : Activities.Activity [Plain]
  - RepeatForever : Activities.Activity<Boolean> [Plain]  // Repeat forever
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OnUiElementAppear
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - WaitVisible : Boolean [In]  // Wait visible
  - WaitActive : Boolean [In]  // Wait active
  - FoundElement : UiPath.Core.UiElement [Out]  // Found element
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Body : Activities.Activity [Plain]
  - RepeatForever : Activities.Activity<Boolean> [Plain]  // Repeat forever
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OnUiElementVanish
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - WaitNotVisible : Boolean [In]  // Wait not visible
  - WaitNotActive : Boolean [In]  // Wait not active
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Body : Activities.Activity [Plain]
  - RepeatForever : Activities.Activity<Boolean> [Plain]  // Repeat forever
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OpenApplication
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Selector** : String [In]  // Selector
- optional:
  - FileName : String [In]  // File
  - Arguments : String [In]  // Arguments
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - ApplicationWindow : UiPath.Core.Window [Out]  // Application window
  - WorkingDirectory : String [In]  // Working directory
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - InformativeScreenshot : String [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.OpenBrowser
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Url** : String [In]  // Url
- optional:
  - Private : Boolean [In]  // Private
  - NewSession : Boolean [In]  // New session
  - Hidden : Boolean [In]  // Property hidden
  - BrowserType : UiPath.Core.BrowserType [In]  // Browser type
  - CommunicationMethod : UiPath.Core.CommMethod [In] = 0  // Communication method
  - UserDataFolderMode : UiPath.UIAutomationNext.Enums.BrowserUserDataFolderMode [In]  // User data folder mode
  - UserDataFolderPath : String [In]  // User data folder path
  - AutomaticallyDownloadWebDriver : Boolean [In]  // Automatically download web driver
  - UiBrowser : UiPath.Core.Browser [Out]  // Ui browser
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - InformativeScreenshot : String [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.PropertyNotSetException
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Message : String [Plain]
  - IsWarning : Boolean [Plain]
  - PropertyName : String [Plain]
  - Id : String [Plain]
  - Source : Activities.Activity [Plain]
  - SourceDetail : Object [Plain]

## UiPath.Core.Activities.RefreshBrowser
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Browser : UiPath.Core.Browser [In]  @group=Browser  // Browser
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RegistrationException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.ReplayUserEvent
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - InterceptedEvent : Object [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ReplayUserEventV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **EventInfo** : UiPath.Core.EventInfo [In]  // Event info
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.RestoreWindow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Window : UiPath.Core.Window [In]  @group=Use Window  // Window
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.CallTransaction
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Transaction** : String [In]  // Transaction code
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.ClickPictureOnScreen
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - PictureOffsetX : Int32 [In]  // Picture offset x
  - PictureOffsetY : Int32 [In]  // Picture offset y
  - SendWindowMessages : Boolean [In]  // Send window messages
  - ClickType : UiPath.Core.ClickType [In]  // TipoDeClique
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.ClickToolbarButton
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Item** : String [In]  // Button
- optional:
  - Items : Collections.Generic.List<String> [Plain]
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayAfter : Int32 [In]  // AtrasoApós
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.ExpandALVHierarchicalTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UiElement : UiPath.Core.UiElement [Out]  // Ui element
  - FocusedColumn : String [In]  // Focused column
  - ColumnNameLevel0 : String [In]  // Header column
  - ColumnNameLevel1 : String [In]  // Position column
  - ColumnValueLevel0 : String [In]  // Header value
  - ColumnValueLevel1 : String [In]  // Position value
  - AllColumns : Collections.Generic.List<String> [Plain]
  - ColumnsLevel0 : Collections.Generic.List<String> [Plain]
  - ColumnsLevel1 : Collections.Generic.List<String> [Plain]
  - SelectLevel1 : Boolean [Plain]
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.ExpandALVTree
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Path** : String [In]  // Tree path
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.ExpandTree
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Item** : String [In]  // Item
- optional:
  - Items : Collections.Generic.List<String> [Plain]
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayAfter : Int32 [In]  // AtrasoApós
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.Login
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Username** : String [In]  // User
  - **Client** : String [In]  // Client
  - **Language** : String [In]  // Language
  - **Timeout** : Int32 [In]  // TempoLimiteEmMs
  - **MultiLogonOptionToChoose** : UiPath.Core.Activities.SAP.MultiLogonOption [Plain]  // Multi logon option
- optional:
  - SecurePassword : Security.SecureString [In]  // Secure password
  - Password : String [In]  // Password
  - IsSecure : Boolean [Plain]  // Is secure
  - Window : UiPath.Core.Window [Out]  // Sap session window
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.Logon
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SAPLogonPath** : String [In]  // Logon path
  - **ConnectionName** : String [In]  // Logon connection
- optional:
  - Retries : Int32 [In]  // Number of retries
  - DelayBetweenRetries : Int32 [In]  // Retry interval
  - Window : UiPath.Core.Window [Out]  // Sap login window
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.ReadStatusbar
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - MessageType : String [Out]  // Statusbar message type
  - MessageText : String [Out]  // Statusbar message text
  - MessageId : String [Out]  // Statusbar message id
  - MessageNumber : String [Out]  // Statusbar message number
  - MessageData : String[] [Out]  // Statusbar message data
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.SelectDatesInCalendar
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SelectType** : UiPath.Core.Activities.SAP.DateSelectionType [In]  // Select dates in calendar select
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - Date : DateTime [In]  // Select dates in calendar date
  - StartDate : DateTime [In]  // Select dates in calendar start date
  - EndDate : DateTime [In]  // Select dates in calendar end date
  - Year : Int32 [In]  // Select dates in calendar year
  - Week : Int32 [In]  // Select dates in calendar week
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAP.SelectMenuItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Item** : String [In]  // Menu
- optional:
  - Items : Collections.Generic.List<String> [Plain]
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayAfter : Int32 [In]  // AtrasoApós
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SAPCallTransactionException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.SAPLoginException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.SapSessionTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Attributes** : String[] [In]  // Attributes

## UiPath.Core.Activities.SaveImage
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **FileName** : String [In]  // File
  - **Image** : UiPath.Core.Image [In]  // Imagem 
- optional:
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SelectItem
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Item** : String [In]  // Item
- optional:
  - Items : Collections.Generic.List<String> [Plain]
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayAfter : Int32 [In]  // AtrasoApós
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SelectMultipleItems
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **MultipleItems** : String[] [In]  // Multiple items
- optional:
  - AddToSelection : Boolean [In] = false  // Add to selection
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayAfter : Int32 [In]  // AtrasoApós
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SendHotkey
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - Key : String [In]  // Key
  - SpecialKey : Boolean [In]  // Special key
  - SendWindowMessages : Boolean [In]  // Send window messages
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayBetweenKeys : Int32 [In]  // AtrasoEntreChaves
  - ClickBeforeTyping : Boolean [In]  // ClicarAntesDeDigitar
  - EmptyField : Boolean [In]  // CampoVazio
  - Activate : Boolean [In]  // Activate
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetAttribute`1
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - AttributeName : String [In]  // Attribute
  - AttributeValue : T [In]  // Attribute value
  - Element : UiPath.Core.UiElement [In]  // Elemento
  - DelayAfter : Int32 [In]  // AtrasoApós
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetClippingRegion
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Direction : UiPath.Core.Direction [In]  // Direction
  - Size : UiPath.Core.Region [Plain]  // Size
  - Region : UiPath.Core.Region [In]  // Region
  - Element : UiPath.Core.UiElement [In]  // Elemento
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetFocus
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetToClipboard
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
- optional:
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetValue
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
- optional:
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayAfter : Int32 [In]  // AtrasoApós
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SetWebAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Attribute** : String [In]  // Attribute
  - **Value** : String [In]  // Value
- optional:
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayAfter : Int32 [In]  // AtrasoApós
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.ShowWindow
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Window : UiPath.Core.Window [In]  @group=Use Window  // Window
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.StartProcess
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FileName : String [In]  // File
  - Arguments : String [In]  // Arguments
  - WorkingDirectory : String [In]  // Working directory
  - StartType : UiPath.Core.Activities.StartProcessType [In]  // Start process type
  - Timeout : Int32 [In]  // TempoLimiteEmMs
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.StartProcessType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.StateChangedEvent
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.SystemTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - TriggerInput : UiPath.Core.Activities.Input [In]  // Trigger input
  - EventMode : UiPath.Core.EventMode [In]  // Event mode
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.SystemTriggerV2
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - TriggerInput : UiPath.Core.Activities.Input [In]  // Trigger input
  - BlockEvent : Boolean [In]  // Block event

## UiPath.Core.Activities.TakeScreenshot
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Screenshot : UiPath.Core.Image [Out]  // Screenshot
  - WaitBefore : Int32 [In]  // Wait before
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.Target
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Selector : String [In]  // Selector
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - WaitForReady : UiPath.Core.WaitForReady [In]  // Wait for ready
  - Element : UiPath.Core.UiElement [In]  // Elemento
  - ClippingRegion : UiPath.Core.Region [Plain]  // Clipping region
  - InformativeScreenshot : String [Plain]
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Id : Guid [Plain]
  - IsUsedAsImplementation : Boolean [Plain]

## UiPath.Core.Activities.TargetFindCriteria
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Context : Activities.ActivityContext [Plain]
  - BaseElement : UiPath.Core.UiElement [Plain]
  - Selector : String [Plain]
  - Timeout : Nullable<Int32> [Plain]
  - SkipAnchor : Boolean [Plain]

## UiPath.Core.Activities.TextExists
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Occurrence** : Int32 [In]  // Occurrence
- optional:
  - FormattedText : Boolean [In]  // Formatted text
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TextNotFoundException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.TypeInto
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Text** : String [In]  // Texto
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - DeselectAfter : Boolean [In]
  - SimulateType : Boolean [In]  // Simulate type
  - SendWindowMessages : Boolean [In]  // Send window messages
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayBetweenKeys : Int32 [In]  // AtrasoEntreChaves
  - ClickBeforeTyping : Boolean [In]  // ClicarAntesDeDigitar
  - EmptyField : Boolean [In]  // CampoVazio
  - Activate : Boolean [In]  // Activate
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.TypeSecureText
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **SecureText** : Security.SecureString [In]  // Secure text
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - DeselectAfter : Boolean [In]
  - SimulateType : Boolean [In]  // Simulate type
  - SendWindowMessages : Boolean [In]  // Send window messages
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayBetweenKeys : Int32 [In]  // AtrasoEntreChaves
  - ClickBeforeTyping : Boolean [In]  // ClicarAntesDeDigitar
  - EmptyField : Boolean [In]  // CampoVazio
  - Activate : Boolean [In]  // Activate
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.UIAArgumentSettingAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - SettingsKey : String [Plain]
  - Section : String [Plain]
  - Property : String [Plain]
  - DefaultValue : Object [Plain]
  - Required : Boolean [Plain]
  - TrueOnlyIfNew : Boolean [Plain]

## UiPath.Core.Activities.UIAutomationXamlMigration
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - NamespacesToRemove : Collections.Generic.IEnumerable<String> [Plain]
  - NamespacesToAdd : Collections.Generic.IEnumerable<String> [Plain]
  - AssemblyReferencesToRemove : Collections.Generic.IEnumerable<String> [Plain]
  - AssemblyReferencesToAdd : Collections.Generic.IEnumerable<String> [Plain]

## UiPath.Core.Activities.UiElementExists
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Exists : Boolean [Out]  // Exists
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.UiExplorerLauncher
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.UseForegroundScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - WaitForeground : TimeSpan [In]  // Wait foreground
  - Body : Activities.ActivityAction<Object> [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.WaitAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Attribute** : String [In]  // Attribute
  - **AttributeValue** : Object [In]  // Attribute value
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Element : UiPath.Core.UiElement [In]  // Elemento
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.WaitImageAppear
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - FoundElement : UiPath.Core.UiElement [Out]  // Found element
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisableValidationErrors : Boolean [Plain] = false
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.WaitImageVanish
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - DisableValidationErrors : Boolean [Plain] = false
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.WaitUiElementAppear
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - FoundElement : UiPath.Core.UiElement [Out]  // Found element
  - WaitVisible : Boolean [In]  // Wait visible
  - WaitActive : Boolean [In]  // Wait active
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.WaitUiElementVanish
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - WaitNotVisible : Boolean [In]  // Wait not visible
  - WaitNotActive : Boolean [In]  // Wait not active
  - Target : UiPath.Core.Activities.Target [Plain]  // Destino
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.Activities.WindowNotSetException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Activities.WindowScope
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Selector : String [In]  // Selector
  - SearchScope : UiPath.Core.Window [In]  // Search scope
  - Window : UiPath.Core.Window [In]  // Window
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - ApplicationWindow : UiPath.Core.Window [Out]  // Application window
  - Reference : String [Plain]
  - ContentHash : String [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - InformativeScreenshot : String [Plain]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Core.ActivityVersion
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.AdjustmentCostBasedEvaluator
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Matcher : UiPath.Core.IAttributeMatcher [Plain]

## UiPath.Core.AdjustmentCostBasedScoreAssigner
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.AnchorPosition
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.AttributeEventHandler
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.AttributeEventInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Value : Object [Plain]

## UiPath.Core.AttributeProbabilityAssigner
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.BlockMethod
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Browser
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Timeout : Int32 [Plain]
  - Element : UiPath.Core.UiElement [Plain]
  - BrowserName : UiPath.Core.BrowserType [Plain]
  - ShowDetailedSearchError : Boolean [Plain]

## UiPath.Core.BrowserOperationException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.BrowserType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.ButtonFlags
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.ClickType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.CommMethod
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.CoreAPIException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.CorrectionMode
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Direction
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.ElementOperationException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.ElementPurpose
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.EventInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Forward : UiPath.Core.EventMode [Plain]
  - MonitorID : Int32 [Plain]
  - ScanCode : Int32 [Plain]
  - Position : UiPath.Core.Region [Plain]
  - TargetNode : UiPath.Core.UiElement [Plain]
  - TargetWindow : UiPath.Core.Window [Plain]
  - ReplayEvent : Boolean [Plain]
  - KeyEventInfo : UiPath.Core.KeyEventInfo [Plain]
  - MouseEventInfo : UiPath.Core.MouseEventInfo [Plain]
  - KeyModifier : UiPath.Core.KeyModifier [Plain]
  - AttributeEventInfo : UiPath.Core.AttributeEventInfo [Plain]
  - SapSessionAttributesInfo : UiPath.Core.SapSessionAttributesInfo [Plain]

## UiPath.Core.EventMode
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.EventType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.FindElementException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.FindScope
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.FindStringMethod
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.HierarchyElement
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Element : UiPath.Core.UiElement [Plain]
  - Tag : UiPath.Core.SelectorTag [Plain]

## UiPath.Core.HighlightMode
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Image
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UiImage : UiPath.Vision.UiImage [Plain]
  - Base64 : String [Plain]
  - ByteArray : Byte[] [Plain]
  - Hash : String [Plain]
  - Width : Int32 [Plain]
  - Height : Int32 [Plain]

## UiPath.Core.ImageOperationException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InputAction
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InputMethod
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InvalidBrowserException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InvalidImageException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InvalidRegionException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InvalidScrapeOptionsException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InvalidSelectorException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InvalidUiElementException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.InvalidWindowException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.KeyboardEventHandler
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.KeyEventInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Key : Windows.Input.Key [Plain]
  - KeyAction : UiPath.Core.InputAction [Plain]
  - KeyName : String [Plain]

## UiPath.Core.KeyModifier
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.MatchResult
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - AttributeName : String [Plain]
  - Arg1 : String [Plain]
  - Arg2 : String [Plain]
  - Score : Single [Plain]
  - CommonValue : String [Plain]

## UiPath.Core.Monitor
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.MouseButton
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.MouseEventHandler
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.MouseEventInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - MouseAction : UiPath.Core.InputAction [Plain]
  - Button : UiPath.Core.MouseButton [Plain]

## UiPath.Core.NormalizedCoordinatesAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.OCREngine
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.OCREngineMode
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Position
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.PrefixAndSufixMatcher
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.ProbabilisticSelectorRepair
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Region
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Rectangle : Nullable<Drawing.Rectangle> [Plain]

## UiPath.Core.Retry
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SapSessionAttributeEventHandler
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SapSessionAttributesInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - SourceSession : String [Plain]
  - Attributes : Collections.Generic.Dictionary<String,Object> [Plain]

## UiPath.Core.SapVKey
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.ScrapeOptions
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - OcrEngine : UiPath.OCR.Contracts.Scrape.ScrapeEngineBase [Plain]
  - OcrLanguage : String [Plain]
  - OcrEngineMode : UiPath.Core.OCREngineMode [Plain]
  - OcrProfile : UiPath.Vision.OCR.OCRProfile [Plain]
  - ScrapingMethod : UiPath.Core.ScrapingMethod [Plain]
  - ExtractInfo : Boolean [Plain]
  - IgnoreHidden : Boolean [Plain]
  - Invert : Boolean [Plain]
  - FormattedText : Boolean [Plain]
  - Separators : String [Plain]
  - AllowedCharacters : String [Plain]
  - DeniedCharacters : String [Plain]
  - OcrScaleLevel : Int32 [Plain]

## UiPath.Core.ScrapeResult
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Text : String [Plain]
  - TextInfo : UiPath.Core.TextInfo[] [Plain]

## UiPath.Core.ScrapingMethod
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.ScreenshotInputMethod
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SelectionOptions
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SelectionType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Selector
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - UseOmit : Boolean [Plain]
  - Text : String [Plain]
  - ParentSelector : UiPath.Core.Selector [Plain]
  - DefaultSerialization : UiPath.Core.SelectorSerializationFlags [Plain]

## UiPath.Core.SelectorAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SelectorNotFoundException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SelectorOperationException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SelectorOptions
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SelectorSerializationFlags
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SelectorStrategy
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SelectorTag
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - IsActive : Boolean [Plain]
  - TagName : String [Plain]

## UiPath.Core.SemanticallyAwareAttributeMatcher
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.SemanticallyAwareScoreEvaluator
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DefaultEvaluator : UiPath.Core.IAttributeScoreEvaluator [Plain]

## UiPath.Core.SimulateEventType
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.TagSerializationFormat
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.TextInfo
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Text : String [Plain]
  - Color : UInt32 [Plain]
  - Region : UiPath.Core.Region [Plain]

## UiPath.Core.TriggerMode
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.UiElement
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Selector : UiPath.Core.Selector [Plain]
  - ClippingRegion : UiPath.Core.Region [Plain]
  - ClippingRegion_Normalized : UiPath.Core.Region [Plain]
  - ImageBase64 : String [Plain]
  - Timeout : Int32 [Plain]
  - WaitForReadyLevel : UiPath.Core.WaitForReady [Plain]
  - Attributes : String[] [Plain]
  - Activate : Boolean [Plain]
  - AlterIfDisabled : Boolean [Plain]
  - ScaleFactor : Double [Plain]
  - AppZoomFactor : Double [Plain]
  - DisplayDpiScaleFactor : Double [Plain]
  - UseNonBlockingInput : Boolean [Plain]
  - SelectorStrategy : UiPath.Core.SelectorStrategy [Plain]
  - options : UiPath.Core.SelectorOptions [Plain]

## UiPath.Core.UiElementEventHandler
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.UiElementHasNoItemsException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.UiSearchResult
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - element : UiPath.Core.UiElement [Plain]
  - matchingScore : Double [Plain]

## UiPath.Core.UninitializedNodeException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.WaitForReady
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Core.Window
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Handle : IntPtr [Plain]

## UiPath.Core.WindowOperationException
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.CV.Activities.CvCheckWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ScrollDirection : UiPath.CV.Scroll [In]  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In]  // NúmeroDeRolagens
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - InRegion : Drawing.Rectangle [In]
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - Action : UiPath.Core.Activities.CheckType [In]  // Ação
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // TipoDeMovimentoDoCursor
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - InformativeScreenshot : String [Plain]
  - LastCache : UiPath.CV.CVCache [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CVClick
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - TargetType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain]  // TipoDeDestino
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - DesignTimeScaleFactor : Nullable<Double> [Plain]
  - InformativeScreenshot : String [Plain]
  - SimulateClick : Boolean [In]
  - SendWindowMessages : Boolean [In]
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // TipoDeMovimentoDoCursor
  - ClickType : UiPath.Core.ClickType [In]  // TipoDeClique
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - UnblockInput : Boolean [In]  // Unblock input
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CVClickText
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- required:
  - **Text** : String [In]  // Texto
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - FuzzySearch : Boolean [In]  // UsarPesquisaDifusa
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - TargetType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain]
  - InformativeScreenshot : String [Plain]
  - SimulateClick : Boolean [In]
  - SendWindowMessages : Boolean [In]
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]  // Cursor position
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // TipoDeMovimentoDoCursor
  - ClickType : UiPath.Core.ClickType [In]  // TipoDeClique
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - UnblockInput : Boolean [In]  // Unblock input
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CvClickWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ScrollDirection : UiPath.CV.Scroll [In]  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In]  // NúmeroDeRolagens
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - InformativeScreenshot : String [Plain]
  - UnblockInput : Boolean [In]
  - SimulateClick : Boolean [In] = false
  - SendWindowMessages : Boolean [In] = false
  - CursorPosition : UiPath.Core.Activities.CursorPosition [Plain]
  - AlterIfDisabled : Boolean [In]
  - LastCache : UiPath.CV.CVCache [Plain]
  - KeyModifiers : UiPath.Core.Activities.KeyModifiers [In]  // Key modifiers
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // TipoDeMovimentoDoCursor
  - ClickType : UiPath.Core.ClickType [In]  // TipoDeClique
  - MouseButton : UiPath.Core.MouseButton [In]  // BotãoDoMouse
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CvElementExistsWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ScrollDirection : UiPath.CV.Scroll [In]  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In]  // NúmeroDeRolagens
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - Result : Boolean [Out]
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - InformativeScreenshot : String [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - LastCache : UiPath.CV.CVCache [Plain]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CvExtractDataTableWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - ScrollDirection : UiPath.CV.Scroll [In] = 0  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In] = 2  // NúmeroDeRolagens
  - InRegion : Drawing.Rectangle [In]
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - Result : Data.DataTable [Out]  // Resultado
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - AddHeaders : Boolean [In] = true  // AdicionarCabeçalhos
  - RefreshBefore : Boolean [In] = true  // AtualizarAntesDe
  - IgnoreEmptyRows : Boolean [In] = false  // IgnorarLinhasVazias
  - Scroll : Boolean [In] = false  // TabelaRolável
  - ScrollOffset : Drawing.Point [In]  // Deslocamento de Rolagem de conteúdo
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - InformativeScreenshot : String [Plain]
  - LastCache : UiPath.CV.CVCache [Plain]
  - MaxTableScrollHeightInPixels : Int32 [Plain]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CVGetText
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - Result : String [Out]  // Resultado
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - TargetType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain]  // TipoDeDestino
  - Area : Drawing.Rectangle [In]  // Área
  - UseClipboard : UiPath.CV.GetTextClipboardType [Plain]  // UsarÁreaDeTransferência
  - DesignTimeScaleFactor : Nullable<Double> [Plain]
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - InformativeScreenshot : String [Plain]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CvGetTextWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ScrollDirection : UiPath.CV.Scroll [In]  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In]  // NúmeroDeRolagens
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - Scroll : Boolean [In]  // ScrollableContent
  - ScrollOffset : Drawing.Point [In]  // Deslocamento de Rolagem de conteúdo
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - RefreshBefore : Boolean [In] = true  // AtualizarAntesDe
  - Result : String [Out]  // Resultado
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - MethodType : UiPath.CV.GetTextMethodType [Plain] = 0  // Método
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - InformativeScreenshot : String [Plain]
  - LastCache : UiPath.CV.CVCache [Plain]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CVHighlight
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - TargetType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain]  // TipoDeDestino
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - InformativeScreenshot : String [Plain]
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - DesignTimeScaleFactor : Nullable<Double> [Plain]
  - HighlightTime : Int32 [In]  // Highlight time
  - Color : Drawing.Color [Plain]  // Color
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CvHighlightWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ScrollDirection : UiPath.CV.Scroll [In]  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In]  // NúmeroDeRolagens
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - InformativeScreenshot : String [Plain]
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - Target : UiPath.Core.Activities.Target [Plain]
  - LastCache : UiPath.CV.CVCache [Plain]
  - HighlightTime : Int32 [In]  // Highlight time
  - Color : Drawing.Color [Plain]  // Color
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CvHoverWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - HoverTime : Double [In]  // Duração
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ScrollDirection : UiPath.CV.Scroll [In]  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In]  // NúmeroDeRolagens
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // TipoDeMovimentoDoCursor
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - InformativeScreenshot : String [Plain]
  - LastCache : UiPath.CV.CVCache [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CVRefresh
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - IsMoveMouseEnabled : Boolean [Plain] = true  // MoverMouse
  - InformativeScreenshot : String [Plain]
  - DesignTimeCache : UiPath.CV.CVCache [Plain]
  - IsCacheDirty : Boolean [Plain] = false
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CVScope
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- required:
  - **Target** : UiPath.Core.Activities.Target [Plain]  // Destino
- optional:
  - TimeoutMS : Int32 [In]
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - CvMethod : UiPath.CV.CVMethods [In]  // MétodoCV
  - Server : String [In]  // URL 🔗
  - ApiKey : String [In]  // ChaveDaAPI 🔗
  - UseLocalServer : Boolean [In]  // UsarServidorLocal 🔗
  - ScrollOffset : Drawing.Point [In]  // Deslocamento de Rolagem
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DesignTimeCache : UiPath.CV.CVCache [Plain]
  - RequiresDefaultValues : Boolean [Plain] = false
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheContainer : UiPath.CV.CvCacheContainer [Plain]
  - DesignTimeCacheId : String [Plain]
  - ScopeId : String [Plain]
  - SendOnPremData : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CvSelectItemWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- required:
  - **Text** : UiPath.CV.CvString [In]  // Texto
- optional:
  - InRegion : Drawing.Rectangle [In]
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBetweenKeys : Int32 [In]  // AtrasoEntreChaves
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ScrollDirection : UiPath.CV.Scroll [In]  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In]  // NúmeroDeRolagens
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - InformativeScreenshot : String [Plain]
  - LastCache : UiPath.CV.CVCache [Plain]
  - SimulateType : Boolean [In] = false
  - DeselectAfter : Boolean [In]
  - SendWindowMessages : Boolean [In]
  - AlterIfDisabled : Boolean [In]
  - ClickBeforeTyping : Boolean [In]  // ClicarAntesDeDigitar
  - EmptyField : Boolean [In]  // CampoVazio
  - Activate : Boolean [In]  // Activate
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CVTypeInto
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- required:
  - **Text** : String [In]  // Texto
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - TargetType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain]  // TipoDeDestino
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - DesignTimeScaleFactor : Nullable<Double> [Plain]
  - InformativeScreenshot : String [Plain]
  - SimulateType : Boolean [In]
  - DeselectAfter : Boolean [In]
  - SendWindowMessages : Boolean [In]
  - AlterIfDisabled : Boolean [In]  // Alter if disabled
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayBetweenKeys : Int32 [In]  // AtrasoEntreChaves
  - ClickBeforeTyping : Boolean [In]  // ClicarAntesDeDigitar
  - EmptyField : Boolean [In]  // CampoVazio
  - Activate : Boolean [In]  // Activate
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.CvTypeIntoWithDescriptor
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- required:
  - **Text** : UiPath.CV.CvString [In]  // Texto
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - DelayMS : Int32 [In]  // AtrasoApós
  - DelayBetweenKeys : Int32 [In]  // AtrasoEntreChaves
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - Descriptor : UiPath.CV.CvDescriptor [In]  // Descritor
  - ScrollDirection : UiPath.CV.Scroll [In]  // DireçãoDeRolagem
  - NumberOfScrolls : Int32 [In]  // NúmeroDeRolagens
  - DelayScreenshotAfterScroll : Int32 [In]  // AtrasoNaCapturaDeTelaApósRolagem
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeScaleFactor : Double [In]
  - DesignTimeDescriptor : UiPath.CV.CvDescriptor [Plain]
  - Version : UiPath.CV.FeatureVersion [Plain] = 0
  - DesignTimeCacheId : String [Plain]
  - DesignTimeIsValid : Nullable<Boolean> [Plain]
  - InformativeScreenshot : String [Plain]
  - LastCache : UiPath.CV.CVCache [Plain]
  - SimulateType : Boolean [In] = false
  - DeselectAfter : Boolean [In]
  - SendWindowMessages : Boolean [In]
  - AlterIfDisabled : Boolean [In]
  - ClickBeforeTyping : Boolean [In]  // ClicarAntesDeDigitar
  - EmptyField : Boolean [In]  // CampoVazio
  - Activate : Boolean [In]  // Activate
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - TelemetryActivityType : Type [Plain]
  - SendTelemetryOnlyOnFailure : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.FindCVElement
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- required:
  - **TargetType** : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain]  // TipoDeDestino
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - Image : UiPath.Core.Activities.ImageTarget [Plain]  // Imagem 
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - Result : UiPath.Core.UiElement [Out]
  - Target : UiPath.Core.Activities.Target [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - DesignTimeScaleFactor : Nullable<Double> [Plain]
  - InformativeScreenshot : String [Plain]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.FindCVText
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- required:
  - **Text** : String [In]  // Texto
- optional:
  - TimeoutMS : Int32 [In]  // TempoLimiteEmMs
  - FuzzySearch : Boolean [In]  // UsarPesquisaDifusa
  - Occurrence : Int32 [In] = 0  // Ocorrência
  - ContinueOnError : Boolean [In]  // ContinuarComErro
  - DelayBefore : Int32 [In]  // AtrasoAntes
  - DelayMS : Int32 [In]  // AtrasoApós
  - Result : UiPath.Core.UiElement [Out]
  - InRegion : Drawing.Rectangle [In]  // RegiãoDeEntrada
  - OutRegion : Drawing.Rectangle [Out]  // RegiãoDeSaída
  - InformativeScreenshot : String [Plain]
  - DesignTimeRectangle : Drawing.Rectangle [Plain]
  - TargetType : UiPath.UIAutomationNext.Models.CV.UIVisionCategoryType [Plain]
  - Target : UiPath.Core.Activities.Target [Plain]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.CV.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`

## UiPath.CV.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - Description : String [Plain]

## UiPath.CV.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/cv`
- optional:
  - DisplayName : String [Plain]

## UiPath.Semantic.Activities.Enums.ExtractUnstructuredDataInputType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.Semantic.Activities.Enums.WebEditableElementType
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.Semantic.Activities.NExtractFormDataGeneric`1
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - FieldMappings : Collections.Generic.IDictionary<String,String> [Plain]
  - FormData : T [Out]  // Property semantic form data
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Semantic.Activities.NFillForm
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DataSource : Object [In]  // Property data source
  - EnableValidation : Boolean [Plain] = false  // Property enable validation
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Semantic.Activities.NSetValue
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Value : String [In]  // Property value
  - EnableValidation : Boolean [Plain] = false  // Property enable validation
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Semantic.Activities.NUITask
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Task : String [In]  // Property task
  - Prompt : Collections.Generic.IEnumerable<Activities.InArgument<String>> [Plain]
  - AgentType : UiPath.UIAutomationNext.Enums.NUITaskAgentType [In]  // Property agent type
  - Result : String [Out]  // Property task result
  - CustomConfiguration : String [In]  // Property custom configuration
  - ClipboardMode : UiPath.UIAutomationNext.Enums.NTypeByClipboardMode [In]  // Property type by clipboard
  - TraceAttachMode : UiPath.UIAutomationNext.Enums.NTraceAttachMode [In]  // Property trace attach mode
  - MaxIterations : Int32 [In]  // Property max iterations
  - IsDOMEnabled : Boolean [In]
  - IsVariableSecurityDisabled : Boolean [In]
  - ExecutionTrace : String [Out]
  - TraceFiles : UiPath.UIAutomationNext.Models.NUITaskTraceFiles [Out]
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NApplicationCard
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - TargetApp : UiPath.UIAutomationNext.TargetApp [Plain]  // Property target application
  - ContinueOnError : Boolean [In]  // Property continue on error
  - Timeout : Double [In]  // Property timeout
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - InteractionMode : UiPath.UIAutomationNext.Enums.NInteractionMode [Plain] = 0  // Property interaction mode
  - AttachMode : UiPath.UIAutomationNext.Enums.NAppAttachMode [Plain] = 0  // Property attach mode
  - OpenMode : UiPath.UIAutomationNext.Enums.NAppOpenMode [In]  // Property open
  - CloseMode : UiPath.UIAutomationNext.Enums.NAppCloseMode [In]  // Property close
  - WindowResize : UiPath.UIAutomationNext.Enums.NWindowResize [Plain] = 0  // Property window resize
  - UserDataFolderMode : UiPath.UIAutomationNext.Enums.BrowserUserDataFolderMode [In]  // Property user data folder mode
  - UserDataFolderPath : String [In]  // Property user data folder path
  - IsIncognito : Boolean [In]  // Property is incognito
  - WebDriverMode : UiPath.UIAutomationNext.Enums.NWebDriverMode [In]  // Property web driver mode
  - DialogHandling : UiPath.UIAutomationNext.DialogHandling [Plain]  // Property dialog handling
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NHealingAgentBehavior [In]  // Property healing agent behaviour
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
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
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
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NBrowserDialogScope
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DialogMessage : String [Out]  // Property dialog message
  - DelayAfter : Double [In]
  - DialogScopeType : UiPath.UIAutomationNext.Enums.NBrowserDialogScopeType [Plain] = 0  // Property dialog scope type
  - DialogResponse : UiPath.UIAutomationNext.Enums.NBrowserDialogResponse [In]  // Property dialog response
  - PromptDialogResponseText : String [In]  // Property prompt dialog response text
  - WaitForDialogToAppearTimeout : Double [In]  // Property wait for dialog to appear timeout
  - Body : Activities.Activity [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Property timeout
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NBrowserFilePickerScope
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayAfter : Double [In]
  - Mode : UiPath.UIAutomationNext.Enums.NBrowserFilePickerScopeMode [Plain] = 0  // Property mode
  - SingleFilePath : String [In]  // Property file path
  - MultiFilePaths : Collections.Generic.List<String> [In]  // Property file paths
  - WaitForDialogToAppearTimeout : Double [In]  // Property wait for dialog to appear timeout
  - Body : Activities.Activity [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Property timeout
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NCheck
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Action : UiPath.UIAutomationNext.Enums.NCheckType [In]  // Property action
  - AlterIfDisabled : Boolean [In]  // Property alter if disabled
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NCheckElement
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Result : Boolean [Out]  // Property check element result
  - DelayBefore : Double [In]
  - DelayAfter : Double [In]
  - Timeout : Double [In]  // Property timeout
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NCheckState
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayAfter : Double [In]
  - ContinueOnError : Boolean [In]
  - Exists : Boolean [Out]  // Property exists
  - Timeout : Double [In]  // Property check state timeout
  - Mode : UiPath.UIAutomationNext.Enums.NCheckStateMode [Plain] = 0  // Property check state mode
  - CheckVisibility : Boolean [Plain] = false  // Property wait visible
  - IfExists : Activities.Activity [Plain]
  - IfNotExists : Activities.Activity [Plain]
  - EnableIfExists : Boolean [Plain] = true
  - EnableIfNotExists : Boolean [Plain] = true
  - IsLoose : Boolean [Plain] = false
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NClick
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Property key modifiers
  - ClickType : UiPath.UIAutomationNext.Enums.NClickType [In]  // Property click type
  - MouseButton : UiPath.UIAutomationNext.Enums.NMouseButton [In]  // Property mouse button
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // Property cursor motion type
  - VerifyOptions : UiPath.UIAutomationNext.Activities.VerifyExecutionOptions [Plain]  // Property verify execution
  - AlterIfDisabled : Boolean [In]  // Property alter if disabled
  - ActivateBefore : Boolean [In]  // Property activate
  - UnblockInput : Boolean [In]  // Property unblock input
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NClickTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Button : UiPath.UIAutomationNext.Enums.NMouseButton [In]  // Property mouse button
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Property key modifiers
  - BlockEvent : Boolean [In]  // Property block event
  - IncludeChildren : Boolean [In]  // Property include children
  - Mode : UiPath.UIAutomationNext.Triggers.NClickTriggerMode [In]  // Property trigger mode
  - SchedulingMode : UiPath.Platform.Triggers.TriggerActionSchedulingMode [Plain]  // Property scheduling mode
  - Enabled : Boolean [Plain]
  - ContinueOnError : Boolean [In]
  - Timeout : Double [In]
  - DelayAfter : Double [In]
  - DelayBefore : Double [In]
  - InUiElement : UiPath.Core.UiElement [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]

## UiPath.UIAutomationNext.Activities.NClosePopup
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - PopupException : Exception [In]  // Property popup detected exception
  - PreferredButtons : String[] [In]  // Property popup preferred buttons
  - PopupHandled : UiPath.UIAutomationNext.Enums.NPopupHandleState [Out]  // Property popup handled
  - PopupAppearTimeout : Double [In]  // Property popup appear timeout
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]
  - EnableAI : Boolean [Plain] = false  // Property popup enable ai
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
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
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Property key modifiers
  - MouseButton : UiPath.UIAutomationNext.Enums.NMouseButton [In]  // Property mouse button
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // Property cursor motion type
  - DestinationTarget : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property destination target
  - DestinationScopeIdentifier : String [Plain]
  - DestinationInScope : Object [In]
  - UseSourceHover : Boolean [In]  // Property hover source
  - DelayBetweenActions : Double [In]  // Property delay between actions
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NElementScope
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayBefore : Double [In]
  - DelayAfter : Double [In]
  - InteractionMode : UiPath.UIAutomationNext.Enums.NInteractionMode [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - ScopeGuid : String [Plain]
  - IsLoose : Boolean [Plain]
  - Timeout : Double [In]  // Property timeout
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NExtractData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- required:
  - **ExtractMetadata** : String [In]  // Property extract metadata
- optional:
  - DataTable : Data.DataTable [InOut]  // Property data table
  - LimitExtractionTo : UiPath.UIAutomationNext.Models.ExtractData.LimitType [Plain]  // Property limit type
  - MaximumResults : Int32 [In]  // Property maximum results
  - NextLink : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property next link
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - DelayBetweenPages : Double [In]  // Property delay between pages
  - ExtractSimilar : Boolean [Plain]
  - AppendResults : Boolean [Plain] = true  // Property append results
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - ExtractDataSettings : String [In]  // Property extract settings
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NExtractDataGeneric`1
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- required:
  - **ExtractMetadata** : String [In]  // Property extract metadata
- optional:
  - AppendResults : Boolean [Plain] = false
  - InputDataTable : Data.DataTable [In]  // Property input data table
  - ExtractedData : T [Out]  // Property data table
  - LimitExtractionTo : UiPath.UIAutomationNext.Models.ExtractData.LimitType [Plain]  // Property limit type
  - MaximumResults : Int32 [In]  // Property maximum results
  - NextLink : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property next link
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - DelayBetweenPages : Double [In]  // Property delay between pages
  - ExtractSimilar : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - ExtractDataSettings : String [In]  // Property extract settings
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NFindElements
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayAfter : Double [In]
  - Timeout : Double [In]  // Property check state timeout
  - FilterTarget : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - Mode : UiPath.UIAutomationNext.Enums.NFindMode [In]  // Property find mode
  - Children : Collections.Generic.IEnumerable<UiPath.Core.UiElement> [Out]  // Property children
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NForEachUiElement
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Variables : Collections.ObjectModel.Collection<Activities.Variable> [Plain]
  - VariablesMetadata : Collections.Generic.Dictionary<String,Collections.Generic.List<UiPath.UIAutomationNext.Activities.Models.VariableMetadata>> [Plain]
  - Body : Activities.ActivityAction<Int32> [Plain]
  - Filter : UiPath.UIAutomationNext.Activities.Models.FilterArgument [Plain]
  - ContinueOnError : Boolean [In]  // Property continue on error
  - NextLink : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property next link
  - ExtractMetadata : String [In]  // Property for each extract metadata
  - ExtractDataSettings : String [In]  // Property for each extract settings
  - LimitExtractionTo : UiPath.UIAutomationNext.Models.ExtractData.LimitType [Plain]  // Property limit type
  - MaximumResults : Int32 [In]  // Property maximum results
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - DelayBetweenPages : Double [In]  // Property delay between pages
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
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
  - Attribute : String [In]  // Property attribute
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetAttributeGeneric`1
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Result : T [Out]  // Property attribute value
  - Attribute : String [In]  // Property attribute
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetBrowserData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Browser : UiPath.Core.Browser [In]  // Property browser
  - BrowserType : UiPath.UIAutomationNext.Enums.NBrowserType [In]  // Property browser type
  - SourceUserDataFolder : String [In]  // Property source user data folder
  - UserProfile : String [In]  // Property user profile
  - SessionData : String [Out]  // Property session data
  - Timeout : Double [In]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
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
  - Result : String [Out]  // Output to
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetText
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DisableExternalTools : Boolean [Plain]
  - ScrapingOptions : UiPath.UIAutomationNext.Enums.NScrapingOptions [In]
  - ScrapingMethod : UiPath.UIAutomationNext.Enums.NScrapingMethod [Plain] = 0  // Property scraping method
  - Text : ? [Out]  // Property text
  - TextString : String [Out]  // Property text
  - WordsInfo : Collections.Generic.IEnumerable<UiPath.UIAutomationNext.Activities.Models.NWordInfo> [Out]  // Property words info
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NGetUrl
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - WaitForReady : UiPath.UIAutomationNext.Enums.NWaitForReady [In]  // Property wait for ready
  - CurrentUrl : String [Out]  // Property current url
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
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
  - Url : String [In]  // Property url
  - Mode : UiPath.UIAutomationNext.Enums.NGoToUrlMode [Plain] = 0  // Property mode
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
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
  - Color : Drawing.Color [Plain]  // Property color
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NHover
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - HoverTime : Double [In]  // Duração
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // Property cursor motion type
  - VerifyOptions : UiPath.UIAutomationNext.Activities.VerifyExecutionOptions [Plain]  // Property verify execution
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NInjectJsScript
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - InputParameter : String [In]  // Property input parameter
  - ScriptCode : String [In]  // Property script code
  - ScriptOutput : ? [Out]  // Property script output
  - ExecutionWorld : UiPath.UIAutomationNext.Enums.NExecutionWorld [In]  // Property execution world
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NKeyboardShortcuts
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ActivateBefore : Boolean [In]  // Property activate
  - DelayBetweenShortcuts : Double [In]  // Property delay between shortcuts
  - DelayBetweenKeys : Double [In]  // Property delay between keys
  - ClickBeforeMode : UiPath.UIAutomationNext.Enums.NClickMode [In]  // Property click before
  - ShortcutsArgument : String [In]  // Property shortcuts
  - Shortcuts : String [Plain]  // Property shortcuts
  - VerifyOptions : UiPath.UIAutomationNext.Activities.VerifyExecutionOptions [Plain]  // Property verify execution
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NKeyboardTrigger
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Key : String [In]  // Property key
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Property key modifiers
  - BlockEvent : Boolean [In]  // Property block event
  - IncludeChildren : Boolean [In]  // Property include children
  - Mode : UiPath.UIAutomationNext.Triggers.NKeyTriggerMode [In]  // Property trigger mode
  - SchedulingMode : UiPath.Platform.Triggers.TriggerActionSchedulingMode [Plain]  // Property scheduling mode
  - Enabled : Boolean [Plain]
  - ContinueOnError : Boolean [In]
  - Timeout : Double [In]
  - DelayAfter : Double [In]
  - DelayBefore : Double [In]
  - InUiElement : UiPath.Core.UiElement [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]

## UiPath.UIAutomationNext.Activities.NMouseScroll
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Direction : UiPath.UIAutomationNext.Enums.NScrollDirection [In]  // Property scroll direction
  - MovementUnits : Int32 [In]  // Property scroll movement units
  - SearchedElement : UiPath.UIAutomationNext.Activities.SearchedElement [Plain]  // Property searched element
  - CursorMotionType : UiPath.UIAutomationNext.Enums.CursorMotionType [In]  // Property cursor motion type
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Property key modifiers
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NNativeEventTrigger`1
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - EventType : UiPath.UIAutomationNext.Triggers.NNativeEventType [Plain] = 0  // Property event type
  - AvailableEventTypes : String [Plain]
  - MatchSync : Boolean [Plain] = false  // Property match sync
  - IncludeChildren : Boolean [In]  // Property include children
  - Selectors : Collections.Generic.IEnumerable<String> [In]  // Property selectors
  - SchedulingMode : UiPath.Platform.Triggers.TriggerActionSchedulingMode [Plain]  // Property scheduling mode
  - Enabled : Boolean [Plain]
  - ContinueOnError : Boolean [In]
  - Timeout : Double [In]
  - DelayAfter : Double [In]
  - DelayBefore : Double [In]
  - InUiElement : UiPath.Core.UiElement [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]

## UiPath.UIAutomationNext.Activities.NNavigateBrowser
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Action : UiPath.UIAutomationNext.Enums.NNavigateBrowserAction [Plain] = 0  // Property action
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
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
  - Transaction : String [In]  // Property transaction
  - Prefix : String [In]  // Property prefix
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPClickPictureOnScreen
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - KeyModifiers : UiPath.UIAutomationNext.Enums.NKeyModifiers [In]  // Property key modifiers
  - ClickType : UiPath.UIAutomationNext.Enums.NClickType [In]  // Property click type
  - AlterIfDisabled : Boolean [In]  // Property alter if disabled
  - ActivateBefore : Boolean [In]  // Property activate
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPClickToolbarButton
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Item : String [In]  // Property toolbar button
  - Items : Collections.Generic.List<String> [Plain]
  - AlterIfDisabled : Boolean [In]  // Property alter if disabled
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPExpandALVHierarchicalTable
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - FocusedColumn : String [In]  // Property focused column
  - ColumnNameLevel0 : String [In]  // Property header column
  - ColumnNameLevel1 : String [In]  // Property position column
  - ColumnValueLevel0 : String [In]  // Property header value
  - ColumnValueLevel1 : String [In]  // Property position value
  - AllColumns : Collections.Generic.List<String> [Plain]
  - SelectLevel1 : Boolean [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPExpandALVTree
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Path : String [In]  // Property tree path
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPExpandTree
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Item : String [In]  // Property tree item
  - Items : Collections.Generic.List<String> [Plain]
  - AlterIfDisabled : Boolean [In]  // Property alter if disabled
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPLogin
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Username : String [In]  // Property user
  - SecurePassword : Security.SecureString [In]  // Property secure password
  - Password : String [In]  // Property password
  - Client : String [In]  // Property client
  - Language : String [In]  // Property language
  - Option : UiPath.UIAutomationNext.Enums.NMultiLogonOption [Plain]  // Property multi logon option
  - IsSecure : Boolean [Plain] = false  // Property is secure
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property sap session window
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPLogon
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Retries : Int32 [In]  // Property sap logon number of retries
  - DelayBetweenRetries : Double [In]  // Property sap logon retry interval
  - InUiElement : UiPath.Core.UiElement [In]
  - UserDataFolderMode : UiPath.UIAutomationNext.Enums.BrowserUserDataFolderMode [In]
  - UserDataFolderPath : String [In]
  - IsIncognito : Boolean [In]
  - WebDriverMode : UiPath.UIAutomationNext.Enums.NWebDriverMode [In]
  - OCREngine : Activities.ActivityFunc<Drawing.Image,Collections.Generic.IEnumerable<Collections.Generic.KeyValuePair<Drawing.Rectangle,String>>> [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - TargetApp : UiPath.UIAutomationNext.TargetApp [Plain]  // Property target application
  - ContinueOnError : Boolean [In]  // Property continue on error
  - Timeout : Double [In]  // Property timeout
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - InteractionMode : UiPath.UIAutomationNext.Enums.NInteractionMode [Plain] = 0  // Property interaction mode
  - AttachMode : UiPath.UIAutomationNext.Enums.NAppAttachMode [Plain] = 0  // Property attach mode
  - OpenMode : UiPath.UIAutomationNext.Enums.NAppOpenMode [In]  // Property open
  - CloseMode : UiPath.UIAutomationNext.Enums.NAppCloseMode [In]  // Property close
  - WindowResize : UiPath.UIAutomationNext.Enums.NWindowResize [Plain] = 0  // Property window resize
  - DialogHandling : UiPath.UIAutomationNext.DialogHandling [Plain]  // Property dialog handling
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NHealingAgentBehavior [In]  // Property healing agent behaviour
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
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPReadStatusbar
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - MessageType : String [Out]  // Property sap read statusbar message type label
  - MessageText : String [Out]  // Property sap read statusbar message text label
  - MessageId : String [Out]  // Property sap read statusbar message id label
  - MessageNumber : String [Out]  // Property sap read statusbar message number label
  - MessageData : String[] [Out]  // Property sap read statusbar message data label
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPSelectDatesInCalendar
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - SelectType : UiPath.UIAutomationNext.Enums.NDateSelectionType [In]  // Property sap select dates in calendar select
  - Date : DateTime [In]  // Property sap select dates in calendar date
  - StartDate : DateTime [In]  // Property sap select dates in calendar start date
  - EndDate : DateTime [In]  // Property sap select dates in calendar end date
  - Year : Int32 [In]  // Property sap select dates in calendar year
  - Week : Int32 [In]  // Property sap select dates in calendar week
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPSelectMenuItem
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Item : String [In]  // Property menu item
  - AlterIfDisabled : Boolean [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Items : Collections.Generic.List<String> [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSAPTableCellScope
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ColumnName : String [In]  // Property column
  - RowIndex : UInt32 [In]  // Property row index
  - RowSelector : String [In]  // Property row selector
  - RowType : UiPath.UIAutomationNext.Enums.NSAPTableCellScopeRowType [In]  // Property row type
  - TableRow : UInt32 [Out]  // Property table row
  - ColumnNames : Collections.Generic.IEnumerable<String> [Plain]
  - Body : Activities.ActivityAction<Object> [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
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
  - Item : String [In]  // Property item
  - Items : Collections.Generic.List<String> [Plain]
  - AlterIfDisabled : Boolean [In]  // Property alter if disabled
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSetBrowserData
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Browser : UiPath.Core.Browser [In]  // Property browser
  - SessionData : String [In]  // Property session data
  - Timeout : Double [In]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSetClipboard
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Text : String [In]  // Texto
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSetFocus
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NSetRuntimeBrowser
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - BrowserType : UiPath.UIAutomationNext.Enums.NBrowserType [In]  // Property browser type
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - InUiElement : UiPath.Core.UiElement [In]
  - OutUiElement : UiPath.Core.UiElement [Out]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
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
  - Text : String [In]  // Property text
  - CacheTargetElement : Boolean [Plain] = false  // Property cache target element
  - AlterIfDisabled : Boolean [In]  // Property alter if disabled
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NTakeScreenshot
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DelayBeforeScreenshot : Double [In]  // Property delay before screenshot
  - FileName : String [In]  // Property file
  - FileNameMode : UiPath.UIAutomationNext.Enums.NFileNameMode [In]  // Property file name mode
  - SavedTo : ? [Out]  // Property saved to
  - OutImage : UiPath.Core.Image [Out]  // Property out image
  - SaveScreenshotTo : UiPath.UIAutomationNext.Enums.NSaveScreenshotTo [Plain] = 0
  - DelayAfter : Double [In]
  - OutFile : UiPath.Platform.ResourceHandling.ILocalResource [Out]  // Property out file
  - Timeout : Double [In]  // Property timeout
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NTypeInto
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DisableExternalTools : Boolean [Plain]
  - Text : String [In]  // Property text
  - SecureText : Security.SecureString [In]  // Property secure text
  - DelayBetweenKeys : Double [In]  // Property delay between keys
  - ActivateBefore : Boolean [In]  // Property activate
  - ClickBeforeMode : UiPath.UIAutomationNext.Enums.NClickMode [In]  // Property click before
  - EmptyFieldMode : UiPath.UIAutomationNext.Enums.NEmptyFieldMode [In]  // Property clear before
  - ClipboardMode : UiPath.UIAutomationNext.Enums.NTypeByClipboardMode [In]  // Property type by clipboard
  - DeselectAfter : Boolean [In]  // Property deselect after
  - IsPassword : Boolean [Plain] = false
  - VerifyOptions : UiPath.UIAutomationNext.Activities.VerifyExecutionTypeIntoOptions [Plain]  // Property verify execution
  - AlterIfDisabled : Boolean [In]  // Property alter if disabled
  - InteractionMode : UiPath.UIAutomationNext.Enums.NChildInteractionMode [In]  // Property interaction mode
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]
  - ClickOffset : UiPath.UIAutomationNext.ClickOffset [Plain]
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NUnblockUserInput
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.NWindowOperation
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Operation : UiPath.UIAutomationNext.Enums.NWindowOperationType [In]  // Property operation
  - X : Int32 [In]  // Property x
  - Y : Int32 [In]  // Property y
  - Width : Int32 [In]  // Property width
  - Height : Int32 [In]  // Property height
  - Timeout : Double [In]  // Property timeout
  - DelayAfter : Double [In]  // Property delay after
  - DelayBefore : Double [In]  // Property delay before
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - ContinueOnError : Boolean [In]  // Property continue on error
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - ScopeIdentifier : String [Plain]
  - InScope : Object [In]
  - RequiresInitialization : Boolean [Plain]
  - Version : UiPath.UIAutomationNext.Enums.NActivityVersion [Plain] = 0
  - ForceRefreshView : Boolean [Plain]
  - HealingAgentBehavior : UiPath.UIAutomationNext.Enums.NChildHealingAgentBehavior [In]  // Property healing agent behaviour
  - InUiElement : UiPath.Core.UiElement [In]  // Property in ui element
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.UIAutomationNext.Activities.SearchedElement
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - DisplayName : String [Plain]
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - Timeout : Double [In]  // Property timeout
  - OutUiElement : UiPath.Core.UiElement [Out]  // Property out ui element
  - InUiElement : UiPath.Core.UiElement [In]

## UiPath.UIAutomationNext.Activities.SupportsSpecialKeysAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`

## UiPath.UIAutomationNext.Activities.VerifyExecutionOptions
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - Mode : UiPath.UIAutomationNext.Enums.NVerifyMode [Plain]  // Property verify mode
  - Retry : Boolean [In]  // Property retry
  - Timeout : Double [In]  // Property timeout
  - DelayBefore : Double [In]  // Property delay before
  - DisplayName : String [Plain]  // Property
  - IsLoose : Boolean [Plain] = false

## UiPath.UIAutomationNext.Activities.VerifyExecutionTypeIntoOptions
- xmlns: `http://schemas.uipath.com/workflow/activities/uix`
- optional:
  - ExpectedText : String [In]  // Property expected text
  - Target : UiPath.UIAutomationNext.TargetAnchorable [Plain]  // Property target
  - Mode : UiPath.UIAutomationNext.Enums.NVerifyMode [Plain]  // Property verify mode
  - Retry : Boolean [In]  // Property retry
  - Timeout : Double [In]  // Property timeout
  - DelayBefore : Double [In]  // Property delay before
  - DisplayName : String [Plain]  // Property
  - IsLoose : Boolean [Plain] = false

