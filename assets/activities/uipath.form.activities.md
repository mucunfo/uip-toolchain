# uipath.form.activities
Assembly: UiPath.Forms.Activities v25.10.0.0
PackageVersion: 25.10.0
ActivityCount: 8

## UiPath.Forms.Activities.BringFormToFrontActivity
- optional:
  - FormId : String [Plain]
  - InstanceName : String [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Forms.Activities.ChangeFormPropertiesActivity
- optional:
  - Height : Nullable<Int32> [In]
  - Left : Nullable<Int32> [In]
  - ShowMargin : Nullable<Boolean> [In]
  - TopMost : Nullable<Boolean> [In]
  - Title : String [In]
  - Top : Nullable<Int32> [In]
  - Width : Nullable<Int32> [In]
  - WindowState : Nullable<UiPath.Studio.Forms.Runtime.WindowState> [In]
  - FormId : String [Plain]
  - InstanceName : String [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Forms.Activities.CloseFormActivity
- optional:
  - FormId : String [Plain]
  - InstanceName : String [In]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Forms.Activities.ExecuteScriptActivity
- optional:
  - Source : String [In]
  - FormId : String [Plain]
  - InstanceName : String [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Forms.Activities.GetFormFieldsActivity
- optional:
  - Arguments : Collections.Generic.Dictionary<String,Activities.OutArgument> [Plain]
  - FormId : String [Plain]
  - InstanceName : String [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Forms.Activities.HideFormActivity
- optional:
  - FormId : String [Plain]
  - InstanceName : String [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Forms.Activities.SetFormFieldsActivity
- optional:
  - Arguments : Collections.Generic.Dictionary<String,Activities.InArgument> [Plain]
  - FormId : String [Plain]
  - InstanceName : String [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

## UiPath.Forms.Activities.ShowFormActivity
- optional:
  - Arguments : Collections.Generic.Dictionary<String,Activities.Argument> [Plain]
  - Height : Nullable<Int32> [In]
  - IsAsync : Boolean [Plain]
  - Left : Nullable<Int32> [In]
  - ShowInTaskbar : Nullable<Boolean> [In]
  - ShowMargin : Nullable<Boolean> [In]
  - Title : String [In]
  - Top : Nullable<Int32> [In]
  - TopMost : Nullable<Boolean> [In]
  - Width : Nullable<Int32> [In]
  - WindowState : Nullable<UiPath.Studio.Forms.Runtime.WindowState> [In]
  - FormId : String [Plain]
  - InstanceName : String [In]
  - Result : TResult [Out]
  - ResultType : Type [Plain]
  - DisplayName : String [Plain]
  - Id : String [Plain]

