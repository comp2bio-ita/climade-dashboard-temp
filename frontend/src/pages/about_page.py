import dash
from dash import dcc, html
# get_asset_url: unused while the infographic Img is commented.

# configuring page
dash.register_page(__name__, path="/about")

layout = html.Div(

    children=[
    dcc.Location(id='about', refresh=True),
    html.Div(
        className='containerAbout',
        children=[
            html.Div([
        html.H2("About Climade Dashboard"),
        html.P([
            # outdated: pathotrack.health does not connect (HTTPS timeout). Name kept as text.
            # html.A("PathoTrack", href="http://pathotrack.health/", target="_blank"),
            "PathoTrack was created to address the genomic sequencing gap of emerging and re-emerging arboviral threats. "
            "It aims to increase genomic sequencing capacity by sharing laboratory protocols and training in bioinformatic analysis. "
            "This allows for more arboviral genomic sequences to be produced and made publicly available."
            ]),
        html.P([
            "The CLIMADE Dashboard visualises dengue, chikungunya, and Zika virus genomic surveillance data in near-real time", html.A(" (Silva et al. 2026)", href="https://doi.org/10.21203/rs.3.rs-9889257/v1", target="_blank"), ", with the aim to present a dynamic perspective on the arbovirus outbreaks and epidemics, globally. The ",html.A("CLIMADE consortium",href="https://climade.health/",target="_blank")," identified the genomic sequencing gap of these emerging and re-emerging arboviral threats. The consortium aims to increase genomic sequencing capacity building by sharing laboratory protocols and training in bioinformatic analysis. This would allow for more arboviral genomic sequences to be produced and made publicly available. The CLIMADE Dashboard continues the work of the SARS-CoV-2 Africa dashboard ",html.A("(Xavier et al. 2022)",href="https://www.nature.com/articles/s41564-022-01276-9",target="_blank"),  " and was developed as part of the PathoTrack initiative."
            # outdated: covid-africa.genomic-dash.app does not respond.
            # html.A("SARS-CoV-2 Africa dashboard ",href="https://covid-africa.genomic-dash.app/",target="_blank"),
            # "This is the link for Genome Detective Typing Tool that you should link on the ",html.A("information page", href="https://www.genomedetective.com/app/typingtool/virus/", target="_blank"),"."
        ]),
    ],
    className="mt-4"
    ),
    html.Div([
        html.H3("Data Information"),
        html.H4("Data Source"),
        html.P([
            "The raw data used to produce the visualizations is sourced from GenBank. Samples with no collection date "
            "or duplicated IDs were excluded. The data consists of sub-genomic and full genomic sequence metadata."
            # outdated: Genome Detective is not used by this dashboard; classification is already in MySQL.
            # " The classification of GenBank arboviral genomic sequences was done using ",html.A("Genome Detective Typing tools", href="https://www.genomedetective.com/",target="_blank"),"."
    ]),
        html.H4("Data Structure"),
        html.Ul([
            # outdated: not a download or filter field; CSV key is genbank_sequence_data_id.
            # html.Li("Genome ID: Identification of the genomic sample"),
            html.Li("GenBank Accession: GenBank Accession Identification"),
            html.Li("Collection Date: Date that the genomic sample was collected"),
            html.Li("Country: Country where the genomic sample was collected"),
            # outdated: no Geographic Group column; continent comes from the map geojson.
            # html.Li("Geographic Group: Geographic grouping of the genomic sample"),
            # outdated: each page is one virus; "genetic variant" is serotype/genotype on the spec.
            # html.Li("Pathogen: Genetic variant of the virus")
        ]),

    ]),
    html.Div([
        html.H3("Data Process and Usage"),
        html.H4("How to use this data"),
        html.P(
            "1. The global map shows how many genomes have been reported per country in the current filter. Hover a country for that count and the first and last collection dates. Pie icons on the map show the mix of classifications in that country."
        ),
        html.P(
            "2. After filters are applied, a phylogenetic tree can be requested for the selected GenBank accessions. Tips are coloured by a metadata field from that same selection."
        ),
        html.P(
            "3. The circulating-classifications figure shows the proportion of each classification over time. The filters choose which classifications are displayed."
        ),
        html.P(
            "4. The temporal-spread figure shows sequence counts over time for the same classification axis. These counts are publicly available genomes, not incidence."
        ),
        html.H4("Disclaimer"),
        html.P(
            "Take care when interpreting this data. This data has not been validated and is subject to quality control measures and data processing steps."
        )
    ]),
    html.Div([
        html.H3("Dengue Virus: All Serotypes Dashboard"),
        html.P(
            "Dengue Virus (DENV) is a part of the genus, Flavivirus, and the species Dengue Virus. This is an enveloped, positive-sense RNA containing virus, with a genome of approximately 10.7 kb in length (1,2)."
            "DENV is characterised into four serotypes: DENV-1, DENV-2, DENV-3, and DENV-4. The serotypes share a genomic similarity of 65%, but they remain antigenically distinct, and are subdivided into distinct genotypes (3,4)."
            "DENV-1 contains the genotypes I, II, III, IV, and V; DENV-2 contains I, II, III, IV, V, and VI; DENV-3 contains I, II, III, IV, and V; and DENV-4 contains I, II, III, and IV (5)."
            "Each DENV genotype is further subdivided into major and minor lineages which provides additional temporal and spatial resolution on the DENV genotypes. A major lineage is defined by three main rules: [1] The branch length of the lineage has to be more than 25 mutations, [2] the number of tips in the lineage has to be greater than 15, [3] there should be more than one sister lineage (6)."
        )]),

    html.Div([
        html.H3("Chikungunya Dashboard"),
        html.P(
            "Chikungunya virus (CHIKV) is a part of the genus, Alphavirus, and the species Chikungunya Virus. This is a positive-sense, single stranded RNA virus that contains an envelope, with a genome of approximately 12 kb in length (7,8)."
            # outdated: says four lineages then lists three; current spec is ACL, ECSA, WA.
            # "CHIKV has been characterised into four lineages –  ACL (Asian/Caribean), ECSA (East/ Central/ South African), and WA (West African) (9). The lineages of CHIKV, on phylogenetic trees, are sequences that cluster together based on the geographical origins (9)."
        )]),

    html.Div([
        html.H3("Zika Virus Dashboard"),
        html.P(
            "ZIKV is a part of the genus, Flavivirus, and the species Zika Virus. This is an enveloped, single-stranded, positive-sense RNA virus, with a genome of approximately 10.7 kb in length (10). ZIKV is characterised into two lineages – African and Asian. Through phylogenetic analysis, it was found that both lineages emerged in the late 1800s or early 1900s, from East Africa."
        )]),
 
    ]),
    html.Div([
        html.H3("References"),
        html.Ol([
            html.Li("Qi R, Zhang L, Chi C. Biological characteristics of dengue virus and potential targets for drug design. Acta Biochim Biophys Sin (Shanghai). 2008 Feb;40(2):91–101."),
            html.Li("Roy SK, Bhattacharjee S. Dengue virus: epidemiology, biology, and disease aetiology. Can J Microbiol. 2021 Oct;67(10):687–702."),
            html.Li("Ayolabi CI, Olusola BA, Ibemgbo SA, Okonkwo GO. Detection of Dengue viruses among febrile patients in Lagos, Nigeria and phylogenetics of circulating Dengue serotypes in Africa. Infect Genet Evol. 2019 Nov;75:103947."),
            html.Li("Gubler DJ. Epidemic dengue/dengue hemorrhagic fever as a public health, social and economic problem in the 21st century. Trends Microbiol. 2002 Feb;10(2):100–3."),
            html.Li("Fonseca V, Libin PJK, Theys K, Faria NR, Nunes MRT, Restovic MI, et al. A computational method for the identification of Dengue, Zika and Chikungunya virus species and genotypes. PLoS Negl Trop Dis. 2019 May 8;13(5):e0007231."),
            html.Li("Hill V, Cleemput S, Fonseca V, Tegally H, Brito AF, Gifford R, et al. A new lineage nomenclature to aid genomic surveillance of dengue virus. medRxiv. 2024 May 17;"),
            html.Li("Morrison TE. Reemergence of chikungunya virus. J Virol. 2014 Oct;88(20):11644–7."),
            html.Li("Schwartz O, Albert ML. Biology and pathogenesis of chikungunya virus. Nat Rev Microbiol. 2010 Jul;8(7):491–500."),
            html.Li("Powers AM, Brault AC, Tesh RB, Weaver SC. Re-emergence of Chikungunya and O’nyong-nyong viruses: evidence for distinct geographical lineages and distant evolutionary relationships. J Gen Virol. 2000 Feb;81(Pt 2):471–9."),
            html.Li("Faye O, Freire CCM, Iamarino A, Faye O, de Oliveira JVC, Diallo M, et al. Molecular evolution of Zika virus during its emergence in the 20(th) century. PLoS Negl Trop Dis. 2014 Jan 9;8(1):e2636."),
            html.Li([
                "Silva D, Sitharam N, Guimarães RA, Brant-Ribeiro T, Baxter C, Tegally H, de Oliveira T, Xavier J. CLIMADE Dashboard: an Interactive Tool for Tracking Arboviral Variants in near Real-Time. Research Square [preprint]. 2026. ",
            ]),
        ])
    ])
    ]),