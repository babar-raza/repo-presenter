# Aspose.Email FOSS for .Net

[![NuGet](https://img.shields.io/nuget/v/Aspose.Email.Foss.svg)](https://www.nuget.org/packages/Aspose.Email.Foss/) ![.NET](https://img.shields.io/badge/.net-net8.0-blue.svg) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-email-foss/Aspose.Email-FOSS-for-.Net)](https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-.Net/graphs/contributors)

[![Aspose.Email FOSS for .Net](https://products.aspose.org/media/email/net/banner-readme.png)](https://products.aspose.org/email/net/)

Aspose.Email FOSS for .Net reads and writes MSG and EML email formats. It converts messages between MSG and EML representations and preserves message content such as subject, sender, recipients, and attachments. It inspects the internal structure of MSG files using the CFB format reader. It operates on .NET 8.0 and has no external dependencies.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation & Resources](#documentation--resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## At a Glance

```mermaid
flowchart LR
Product["Aspose.Email FOSS for .Net"]
Product["Aspose.Email FOSS for .Net"] --> Cap1["Read and write MSG files"]
Cap2["Create messages programmatically"]
Cap3["Convert between MSG and EML"]
Cap4["Inspect CFB containers"]
Cap5["Access arbitrary MAPI properties"]
Cap6["Attach recipients and files"]
Product["Aspose.Email FOSS for .Net"] --> Cap2["Create messages programmatically"]
Product["Aspose.Email FOSS for .Net"] --> Cap3["Convert between MSG and EML"]
Product["Aspose.Email FOSS for .Net"] --> Cap4["Inspect CFB containers"]
Product["Aspose.Email FOSS for .Net"] --> Cap5["Access arbitrary MAPI properties"]
Product["Aspose.Email FOSS for .Net"] --> Cap6["Attach recipients and files"]
```

## Key Capabilities

- **Read and write MSG files.** It reads MSG files from streams or files using `MapiMessage.FromStream` and writes them back with Save, exposing the Subject property and other message fields directly.
- **Create messages programmatically.** It creates new messages with `MapiMessage.Create`, sets `SenderName` and `SenderEmailAddress`, adds recipients and attachments, and saves the result to a file.
- **Convert between MSG and EML.** It converts EML files to MSG using `MapiMessage.LoadFromEml` and back to EML with `SaveToEml`, implementing both directions natively without external dependencies.
- **Inspect CFB containers.** It opens CFB containers from files with `CfbReader.FromFile`, reports sector size and directory entry count, and iterates the directory tree with `IterTree`.
- **Access arbitrary MAPI properties.** It accesses arbitrary MAPI properties on message objects using `SetProperty` and `GetPropertyValue`, beyond the strongly-typed properties exposed directly by `MapiMessage`.
- **Attach recipients and files.** It attaches recipients with `AddRecipient` and files with `AddAttachment`, including nested embedded messages via `AddEmbeddedMessageAttachment`.

- **Create, edit, save, and reload complete, high-level mutable message objects** through `MapiMessage`: set `Subject`, `Body`, `HtmlBody`, `SenderName`, and `SenderEmailAddress`, then persist with `Save()` and reload with `FromFile()` or `FromStream()` — a free .NET API for building and processing email messages entirely in memory.
- **Inspect parsing problems** on a loaded message or MSG document through the read-only `ValidationIssues` list, populated whenever strict parsing encounters a structural anomaly.

## Installation

Install the published package from NuGet (`Aspose.Email.Foss`, version 26.7.0):

```bash
dotnet add package Aspose.Email.Foss
```

To work from a source checkout instead, build the clone with dotnet build:

```bash
git clone https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-.Net.git
cd Aspose.Email-FOSS-for-.Net
dotnet build
```

## Dependencies

### Required Package Dependencies

No required third-party package dependencies; in `src/Aspose.Email.Foss/Aspose.Email.Foss.csproj`, no `PackageReference` a consumer would install is declared.

### Native and System Requirements

- Requires .NET `net8.0` (`TargetFramework` in `src/Aspose.Email.Foss/Aspose.Email.Foss.csproj`).

## Quick Start

This example reads a MSG file and prints its subject line using `Aspose.Email.Foss` version 26.7.0 targeting net8.0.

```csharp
using System.IO;
using Aspose.Email.Foss.Msg;

using var stream = File.OpenRead("sample.msg");
var message = MapiMessage.FromStream(stream);
Console.WriteLine(message.Subject);
```

## Additional Examples

The following examples demonstrate creating and saving MSG messages, converting EML to MSG, and inspecting the CFB structure of MSG files.

### Convert an EML File to MSG and Back to EML

```csharp
using System.IO;
using Aspose.Email.Foss.Msg;

using var input = File.OpenRead("message.eml");
var message = MapiMessage.LoadFromEml(input);
using var msgOutput = File.Create("message.msg");
message.Save(msgOutput);
using var emlOutput = File.Create("roundtrip.eml");
message.SaveToEml(emlOutput);
```

<details>
<summary>View Additional Examples</summary>

### Create and Save an MSG Message with Sender, Recipient, and Attachment

```csharp
using System.IO;
using Aspose.Email.Foss.Msg;

var message = MapiMessage.Create("Hello", "Body");
message.SenderName = "Alice";
message.SenderEmailAddress = "alice@example.com";
message.AddRecipient("bob@example.com", "Bob");
using var attachmentStream = new MemoryStream("abc"u8.ToArray());
message.AddAttachment("note.txt", attachmentStream, "text/plain");
using var output = File.Create("hello.msg");
message.Save(output);
```

### Inspect the CFB Container Structure of a MSG File

```csharp
using Aspose.Email.Foss.Cfb;

using var cfb = CfbReader.FromFile("sample.msg");
Console.WriteLine($"Sector size: {cfb.SectorSize}");
Console.WriteLine($"Directory entries: {cfb.DirectoryEntryCount}");

foreach (var (depth, entry) in cfb.IterTree())
{
    Console.WriteLine(new string(' ', depth * 2) + entry.Name);
}
```

The test project covers CFB round-trips, MSG reading, and EML round-trip conversion
(`CfbRoundTripTests`, `MsgReaderTests`, `MapiMessageTests`, `MapiMessageEmlTests`,
`MetadataSmokeTests`). Three runnable example programs — `create_msg_and_eml.cs`, `msg_reader.cs`,
and `msg_summary.cs` — live under [`examples/`](examples/), each with its own project file and
listed in [examples/README.md](examples/README.md); run one directly, for example:

```bash
dotnet run --project examples/create_msg_and_eml/create_msg_and_eml.csproj
```

</details>

## API Reference

Aspose.Email FOSS for .Net provides high-level message handling through `Aspose.Email.Foss.Msg.MapiMessage` and lower-level access via `Aspose.Email.Foss.Cfb.CfbReader` and `Aspose.Email.Foss.Msg.MsgReader`. `MapiMessage` serves as the primary entry point for creating, editing, and converting messages, while `CfbReader` and `MsgReader` expose direct access to the underlying storage formats.

The verified public surface has 29 types.

<details>
<summary>View the Complete Public API Surface</summary>

### Core API

| Class | Description |
| --- | --- |
| `CfbConstants` | CfbConstants provides constant values used in Compound File Binary format processing. |
| `CfbDocument` | CfbDocument represents a Compound File Binary structure and provides methods to load it from files, streams, or readers. |
| `CfbException` | CfbException represents errors that occur during Compound File Binary format processing. |
| `CfbNode` | CfbNode represents a node in a Compound File Binary structure with properties such as name, class identifier, timestamps, and state bits. |
| `CfbReader` | CfbReader provides functionality to read and navigate a Compound File Binary structure, including accessing directory entries, streams, and storage nodes. |
| `CfbStorage` | CfbStorage represents a storage node in a Compound File Binary structure that can contain child storages and streams. |
| `CfbStream` | CfbStream represents a stream node in a Compound File Binary structure that holds binary data. |
| `CfbWriter` | CfbWriter provides functionality to write a Compound File Binary structure. |
| `DirectoryEntry` | DirectoryEntry represents an entry in the directory of a Compound File Binary structure. |
| `DirectoryEntryNameComparer` | DirectoryEntryNameComparer provides a comparer for directory entries based on their names. |
| `Header` | Header represents the header information of a Compound File Binary structure. |
| `MapiAttachment` | MapiAttachment represents an attachment in a MAPI message. |
| `MapiMessage` | MapiMessage represents a MAPI message and provides access to its properties, recipients, and attachments. |
| `MapiProperty` | MapiProperty represents a single property in a MAPI message. |
| `MapiPropertyCollection` | MapiPropertyCollection represents a collection of MAPI properties. |
| `MapiRecipient` | MapiRecipient represents a recipient in a MAPI message. |
| `MsgConstants` | MsgConstants provides constant values used in MSG format processing. |
| `MsgDocument` | MsgDocument represents an MSG format file and provides methods to load it from files, streams, or readers. |
| `MsgException` | MsgException represents errors that occur during MSG format processing. |
| `MsgReader` | MsgReader provides functionality to read and navigate an MSG format file. |
| `MsgStorage` | MsgStorage represents a storage node in an MSG format file. |
| `MsgStream` | MsgStream represents a stream node in an MSG format file. |
| `MsgWriter` | MsgWriter provides functionality to write an MSG format file. |

#### Enumerations

| Enumeration | Description |
| --- | --- |
| `DirectoryColorFlag` | Stores the red-black tree color used by directory sibling links. |
| `DirectoryObjectType` | Classifies the directory entry payload as unallocated, storage, stream, or root storage. |
| `SectorMarker` | Special FAT marker values reserved for sector allocation metadata. |
| `CommonMessagePropertyId` | Common MAPI property identifiers used by the MSG reader and writer for core message semantics, body fields, transport headers, and attachments. |
| `MsgStorageRole` | MsgStorageRole specifies the role of a storage node in an MSG format file. |
| `PropertyTypeCode` | MAPI property type codes that appear in property tags and stream names in MSG files. |

#### Detailed Member Reference

### Foss

`Aspose.Email.Foss.Msg.MapiMessage` supports creating messages from scratch with Create, loading from files or streams with `FromFile` and `FromStream`, and converting to EML format with `SaveToEml`; it also provides methods like `AddRecipient`, `AddAttachment`, and `AddEmbeddedMessageAttachment` for building message content, along with property access through `SetProperty` and `GetPropertyValue`. `Aspose.Email.Foss.Cfb.CfbReader` enables reading Compound File Binary structures through `FromFile` and `FromStream` constructors, offering iteration over storages and streams via `IterStorages`, `IterStreams`, and `IterTree`, plus direct access to entries and stream data through `GetEntry` and `GetStreamData`. `Aspose.Email.Foss.Msg.MsgReader` provides strict parsing of MSG files with `FromFile` and `FromStream`, exposing validation issues through its `ValidationIssues` property. `Aspose.Email.Foss.Cfb.CfbWriter` offers static methods `ToBytes` and `WriteFile` to serialize `CfbDocument` instances to bytes or files. `Aspose.Email.Foss.Msg.MsgStorageRole` defines the role of MSG storage objects within the message hierarchy.

*From the maintainers' README (not independently verified):*

`MapiMessage` is the primary high-level entry point for creating, editing, and converting
messages; `CfbReader`/`CfbWriter` and `MsgReader`/`MsgWriter`/`MsgDocument` provide direct,
lower-level access to the `Aspose.Email.Foss.Cfb` and `Aspose.Email.Foss.Msg` namespaces the
high-level API is built on. The public surface spans 29 classes and enumerations in a single
module, summarized below.

- `CfbReader` (implements `IDisposable`)
  - `FromFile(path)`, `FromStream(stream)`, `CfbReader(data)`
  - `IterStorages()`, `IterStreams()`, `IterChildren(storageStreamId)`, `IterTree(startStreamId = 0)`, `FindChildByName(storageStreamId, name)`, `ResolvePath(names, startStreamId)`
  - `GetEntry(streamId)`, `GetStreamData(streamId)`
  - Properties: `Header`, `Difat`, `Fat`, `MiniFat`, `DirectoryEntries`, `RootEntry`, `MajorVersion`, `SectorSize`, `MiniSectorSize`, `DirectoryEntryCount`, `FileSize`

- `CfbWriter` (static)
  - `ToBytes(document)`, `WriteFile(document, path)`

- `CfbDocument` / `CfbStorage` / `CfbStream`
  - Build a document in memory with `CfbStorage.AddStorage()`/`AddStream()`, then hand the root `CfbDocument` to `CfbWriter`.

- `MsgReader` (implements `IDisposable`)
  - `FromFile(path, strict)`, `FromStream(stream, strict)`
  - `ValidationIssues: IReadOnlyList<string>`

- `MsgWriter` (static)
  - `ToBytes(document)`, `WriteFile(document, path)`

- `MsgDocument`
  - `FromFile(path, strict)`, `FromStream(stream, strict)`, `ToCfbDocument()`
  - `Root: MsgStorage`

- `MsgStorage`
  - `AddStream(stream)`, `AddStorage(storage)`, `FindStream(name)`, `FindStorage(name)`
  - Properties: `Role: MsgStorageRole`, `Streams: IList<MsgStream>`, `Storages: IList<MsgStorage>`

- `MapiMessage` (implements `IDisposable`)
  - `Create(subject, body, unicodeStrings)`, `FromFile(path, strict)`, `FromStream(stream, strict)`, `FromMsgDocument(document)`
  - `LoadFromEml(path)` / `LoadFromEml(stream)` / `LoadFromEml(data)`
  - `Save()`, `Save(path)`, `Save(stream)`
  - `SaveToEml()`, `SaveToEml(path)`, `SaveToEml(stream)`
  - `AddRecipient(emailAddress, displayName, recipientType)`, `AddAttachment(filename, data, mimeType, contentId)`, `AddAttachment(filename, stream, mimeType, contentId)`, `AddEmbeddedMessageAttachment(message, filename, mimeType)`
  - `SetProperty(propertyId, propertyType, value, flags)`, `GetPropertyValue(propertyId, propertyType, decode)`, `IterProperties()`, `IterPropertyKeys()`
  - Properties: `Subject`, `Body`, `HtmlBody`, `SenderName`, `SenderEmailAddress`, `MessageClass`, `InternetMessageId`, `MessageDeliveryTime`, `Recipients`, `Attachments`, `ValidationIssues`

- `MapiAttachment`
  - `FromBytes(filename, data, mimeType, contentId)`, `FromStream(filename, stream, mimeType, contentId)`, `OpenRead()`
  - Properties: `Filename`, `Data`, `MimeType`, `ContentId`, `IsEmbeddedMessage`, `EmbeddedMessage: MapiMessage?`

- `MapiPropertyCollection`
  - `Set(property)`, `Add(propertyId, propertyType, value, flags)`, `Get(propertyId, propertyType)`, `Remove(propertyId, propertyType)`, `IterProperties()`

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/email/net/)** — The getting started guide covers installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/email/net/)** — The how-to guides and FAQ provide task-focused answers for common MSG, CFB, and EML questions.
- **[Full API reference](https://reference.aspose.org/email/net/)** — The full API reference offers the complete, browsable reference for all 29 public types. It covers all 29 verified public types; the [API Reference](#api-reference) section above covers the essentials.
- **[Public API summary](PUBLIC_API.md)** — The public API summary lists the repository's own stable-namespace and primary-type list.
- **[Changelog](CHANGELOG.md)** — The changelog documents the release history.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-.Net/issues).

## Scope and Limitations

Aspose.Email FOSS for .Net reads and writes local email files in formats supported by the `Aspose.Email.Foss` package version 26.7.0 for net8.0, without connecting to mail servers or providing dedicated APIs for calendar or TNEF content.

- The library does not support IMAP, SMTP, or POP3 protocols and does not connect to mail servers, as it operates on local files only.
- Transport Neutral Encapsulation Format files, commonly named `winmail.dat`, are not parsed or generated.
- Calendar or appointment support is not provided; calendar-specific MAPI properties can be accessed generically via `SetProperty()` or `GetPropertyValue()` only.
- The package requires .NET 8.0 or later and does not support the classic .NET Framework (4.x).

These limitations don't apply to [full-featured Aspose.Email for .Net — Enterprise Edition](https://products.aspose.com/email/net/). It adds broader format and protocol coverage: direct IMAP/SMTP/POP3 mail-server connectivity, TNEF (winmail.dat) support, calendar and appointment APIs, and classic .NET Framework support alongside this edition's MSG, CFB, and EML processing.

## Development and Testing

Aspose.Email FOSS for .Net targets net8.0 and uses the dotnet CLI for building and testing. The test project at `tests/Aspose.Email.Foss.Tests/Aspose.Email.Foss.Tests.csproj` depends on Microsoft.NET.Test.Sdk 17.8.0, xunit 2.5.3, xunit.runner.visualstudio 2.5.3, and coverlet.collector 6.0.0 for running tests and collecting code coverage; these dependencies are not used by the main library project and are never shipped with the published package.

The suite covers 5 test files under `tests/`.

```xml
<PackageReference Include="Aspose.Email.Foss" Version="26.7.0" />
```

Clone the repository and run the xUnit test suite:

```bash
git clone https://github.com/aspose-email-foss/Aspose.Email-FOSS-for-.Net.git
cd Aspose.Email-FOSS-for-.Net
dotnet build src/Aspose.Email.Foss/Aspose.Email.Foss.csproj -c Release
dotnet test tests/Aspose.Email.Foss.Tests/Aspose.Email.Foss.Tests.csproj
```

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification, distribution, sublicensing, and commercial use, provided its copyright and permission notice are retained. The software is provided without warranty.
