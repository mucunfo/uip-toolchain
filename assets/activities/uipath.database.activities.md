# uipath.database.activities
Assembly: UiPath.Database.Activities v0.0.0.0
PackageVersion: 1.5.0
ActivityCount: 12

## UiPath.Database.Activities.BulkInsert
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // TableName
  - **DataTable** : Data.DataTable [In]  // DataTable
- optional:
  - ProviderName : String [In]  // ProviderName
  - ConnectionString : String [In]  // ConnectionString
  - ConnectionSecureString : Security.SecureString [In]  // SecureConnectionString
  - ExistingDbConnection : UiPath.Database.DatabaseConnection [In]  // Existing Connection
  - ContinueOnError : Boolean [In]  // ContinueOnError
  - AffectedRecords : Int64 [Out]  // AffectedRecords
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Database.Activities.BulkUpdate
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // TableName
  - **ColumnNames** : String[] [In]  // ColumnNames
  - **DataTable** : Data.DataTable [In]  // DataTable
- optional:
  - ProviderName : String [In]  // ProviderName
  - ConnectionString : String [In]  // ConnectionString
  - ConnectionSecureString : Security.SecureString [In]  // SecureConnectionString
  - ExistingDbConnection : UiPath.Database.DatabaseConnection [In]  // Existing Connection
  - BulkUpdateFlag : Boolean [Plain] = true  // Atualização em Massa/Lote
  - ContinueOnError : Boolean [In]  // ContinueOnError
  - AffectedRecords : Int64 [Out]  // AffectedRecords
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Database.Activities.ConnectionHelper
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Database.Activities.DatabaseConnect
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **ProviderName** : String [In]  // ProviderName
- optional:
  - ConnectionString : String [In]  // ConnectionString
  - ConnectionSecureString : Security.SecureString [In]  // SecureConnectionString
  - DatabaseConnection : UiPath.Database.DatabaseConnection [Out]  // DatabaseConnection
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Database.Activities.DatabaseDisconnect
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **DatabaseConnection** : UiPath.Database.DatabaseConnection [In]  // DatabaseConnection
- optional:
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Database.Activities.DatabaseTransaction
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - ProviderName : String [In]  // ProviderName
  - ConnectionString : String [In]  // ConnectionString
  - ConnectionSecureString : Security.SecureString [In]  // SecureConnectionString
  - ExistingDbConnection : UiPath.Database.DatabaseConnection [In]  // Existing Connection
  - ContinueOnError : Boolean [In]  // ContinueOnError
  - DatabaseConnection : UiPath.Database.DatabaseConnection [Out]  // DatabaseConnection
  - Body : Activities.Activity [Plain]
  - UseTransaction : Boolean [Plain]  // UseTransaction
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Database.Activities.ExecuteNonQuery
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Sql** : String [In]
- optional:
  - ProviderName : String [In]  // ProviderName
  - ConnectionString : String [In]  // ConnectionString
  - ConnectionSecureString : Security.SecureString [In]  // SecureConnectionString
  - ExistingDbConnection : UiPath.Database.DatabaseConnection [In]  // Existing Connection
  - CommandType : Data.CommandType [Plain]  // CommandType
  - ContinueOnError : Boolean [In]  // ContinueOnError
  - TimeoutMS : Int32 [In]  // Timeout (milliseconds)
  - Parameters : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Parameters
  - AffectedRecords : Int32 [Out]  // AffectedRecords
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Database.Activities.ExecuteQuery
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **Sql** : String [In]
- optional:
  - ProviderName : String [In]  // ProviderName
  - ConnectionString : String [In]  // ConnectionString
  - ConnectionSecureString : Security.SecureString [In]  // SecureConnectionString
  - ExistingDbConnection : UiPath.Database.DatabaseConnection [In]  // Existing Connection
  - CommandType : Data.CommandType [Plain]  // CommandType
  - ContinueOnError : Boolean [In]  // ContinueOnError
  - TimeoutMS : Int32 [In]  // Timeout (milliseconds)
  - Parameters : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]  // Parameters
  - DataTable : Data.DataTable [Out]  // DataTable
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Database.Activities.InsertDataTable
- xmlns: `http://schemas.uipath.com/workflow/activities`
- required:
  - **TableName** : String [In]  // TableName
  - **DataTable** : Data.DataTable [In]  // DataTable
- optional:
  - ProviderName : String [In]  // ProviderName
  - ConnectionString : String [In]  // ConnectionString
  - ConnectionSecureString : Security.SecureString [In]  // SecureConnectionString
  - ExistingDbConnection : UiPath.Database.DatabaseConnection [In]  // Existing Connection
  - ContinueOnError : Boolean [In]  // ContinueOnError
  - AffectedRecords : Int32 [Out]  // AffectedRecords
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Database.Activities.LocalizedCategoryAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`

## UiPath.Database.Activities.LocalizedDescriptionAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - Description : String [Plain]

## UiPath.Database.Activities.LocalizedDisplayNameAttribute
- xmlns: `http://schemas.uipath.com/workflow/activities`
- optional:
  - DisplayName : String [Plain]

