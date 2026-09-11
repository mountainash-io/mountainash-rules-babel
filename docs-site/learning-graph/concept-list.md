# Concept List for Mountainash Rules Babel

Total concepts: 70

## Foundation Concepts (1-10)

1. Decision Tables
2. Business Rules
3. CSV Format
4. XML Format
5. DMN Standard
6. FEEL Language
7. Python Protocols
8. Runtime Checkable Protocol
9. Entry Points Mechanism
10. Lattice Object

## Plugin Architecture (11-17)

11. PluginRegistry Class
12. Auto Discovery
13. Entry Point Groups
14. Exporter Entry Points
15. Importer Entry Points
16. Decomposer Entry Points
17. Validator Entry Points

## Importers (18-25)

18. Importer Protocol
19. Import Name Attribute
20. File Extensions Attribute
21. Import Lattice Method
22. CsvImporter Class
23. Dimension Column Inference
24. Data Type Detection
25. Polars CSV Read

## Exporters (26-47)

26. Exporter Protocol
27. Export Name Attribute
28. File Extension Attribute
29. Export Method
30. Export Bytes Method
31. CsvExporter Class
32. Polars DataFrame Conversion
33. DmnExporter Class
34. DMN XML Tree Construction
35. DMN Definitions Element
36. DMN Decision Element
37. DMN DecisionTable Element
38. DMN Input Elements
39. DMN Output Elements
40. DMN Rule Elements
41. FEEL Expression Mapping
42. FEEL Exact Match
43. FEEL Not Equal
44. FEEL Range Expression
45. FEEL Greater Than
46. FEEL Less Than
47. FEEL Prefix Match

## Exporters — Additional FEEL Mappings (48-53)

48. FEEL Suffix Match
49. FEEL Contains Match
50. FEEL Set Membership
51. FEEL Set Exclusion
52. NA Sentinel Handling
53. XML Security Module

## Validators (54-60)

54. Validator Protocol
55. ValidationIssue Dataclass
56. ValidationReport Dataclass
57. ConflictsValidator
58. CoverageValidator
59. OrphansValidator
60. RoundTripValidator

## Decomposers (61-63)

61. Decomposer Protocol
62. Fragment Dataclass
63. DecompositionResult Dataclass

## CLI Interface (64-67)

64. Typer CLI App
65. Babel Export Command
66. Babel Import Command
67. Babel Validate Command

## Error Handling (68-70)

68. BabelError Base
69. FormatNotFoundError
70. ValidationError Class
