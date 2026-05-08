# uipath.integrationservice.activities
Assembly: UiPath.IntegrationService.Activities.Runtime v1.21.0.0
PackageVersion: 1.21.0
ActivityCount: 16

## UiPath.IntegrationService.Activities.Runtime.Activities.ConnectorActivity
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - FilterValuesDictionary : Collections.Generic.Dictionary<String,UiPath.IntegrationService.Activities.Runtime.Models.FilterBuilder.FilterValuesTree> [Plain]
  - UiPathActivityTypeId : String [Plain]
  - ConnectionId : String [Plain]
  - Configuration : String [Plain]
  - Arguments : Collections.ObjectModel.Collection<UiPath.IntegrationService.Activities.Runtime.Models.FieldArgument> [Plain]
  - FieldObjects : Collections.ObjectModel.Collection<UiPath.IntegrationService.Activities.Runtime.Models.FieldObject> [Plain]
  - BindingsJson : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.IntegrationService.Activities.Runtime.Activities.ConnectorHttpActivity
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - UiPathActivityTypeId : String [Plain]
  - ConnectionId : String [Plain]
  - Configuration : String [Plain]
  - Arguments : Collections.ObjectModel.Collection<UiPath.IntegrationService.Activities.Runtime.Models.FieldArgument> [Plain]
  - FieldObjects : Collections.ObjectModel.Collection<UiPath.IntegrationService.Activities.Runtime.Models.FieldObject> [Plain]
  - BindingsJson : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.IntegrationService.Activities.Runtime.Activities.ConnectorPersistenceActivity
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - BindingsJson : String [Plain]
  - UiPathActivityTypeId : String [Plain]
  - Configuration : String [Plain]
  - FieldObjects : Collections.ObjectModel.Collection<UiPath.IntegrationService.Activities.Runtime.Models.FieldObject> [Plain]
  - InboxId : Nullable<Guid> [In]
  - ConnectionId : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.IntegrationService.Activities.Runtime.Activities.ConnectorTriggerActivity
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - UiPathEventConnector : String [In]
  - UiPathEvent : String [In]
  - UiPathEventObjectType : String [In]
  - UiPathEventObjectId : String [In]
  - UiPathAdditionalEventData : String [In]
  - FilterValues : UiPath.IntegrationService.Activities.Runtime.Models.FilterBuilder.FilterValuesTree [Plain]
  - UiPathActivityTypeId : String [Plain]
  - ConnectionId : String [Plain]
  - Configuration : String [Plain]
  - Arguments : Collections.ObjectModel.Collection<UiPath.IntegrationService.Activities.Runtime.Models.FieldArgument> [Plain]
  - FieldObjects : Collections.ObjectModel.Collection<UiPath.IntegrationService.Activities.Runtime.Models.FieldObject> [Plain]
  - BindingsJson : String [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.IntegrationService.Activities.Runtime.Exceptions.GeneralException
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`

## UiPath.IntegrationService.Activities.Runtime.Exceptions.RuntimeException
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`

## UiPath.IntegrationService.Activities.Runtime.Helpers.DateTimeOffsetMaskDeserializer
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - CanWrite : Boolean [Plain]
  - CanRead : Boolean [Plain]

## UiPath.IntegrationService.Activities.Runtime.Models.ActivityStatus
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`

## UiPath.IntegrationService.Activities.Runtime.Models.EnumItem
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - Name : String [Plain]
  - Value : Object [Plain]

## UiPath.IntegrationService.Activities.Runtime.Models.FieldArgument
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - Name : String [Plain]
  - Argument : ? [In]

## UiPath.IntegrationService.Activities.Runtime.Models.FieldObject
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - Name : String [Plain]
  - Value : Object [Plain]
  - Type : UiPath.IntegrationService.Activities.Runtime.Models.FieldObjectType [Plain]

## UiPath.IntegrationService.Activities.Runtime.Models.FieldObjectType
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`

## UiPath.IntegrationService.Activities.Runtime.Models.FieldSampleValueAttribute
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - Value : Object [Plain]

## UiPath.IntegrationService.Activities.Runtime.Models.FilterBuilder.FilterValuesTree
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`
- optional:
  - Values : Collections.Generic.IList<Object> [Plain]
  - Groups : Collections.Generic.IList<UiPath.IntegrationService.Activities.Runtime.Models.FilterBuilder.FilterValuesTree> [Plain]

## UiPath.IntegrationService.Activities.Runtime.Models.JitObject
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`

## UiPath.IntegrationService.Activities.Runtime.Models.RootJitObject
- xmlns: `http://schemas.uipath.com/workflow/integration-service-activities/isactr`

