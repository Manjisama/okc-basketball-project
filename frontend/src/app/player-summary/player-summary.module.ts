import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';
import {PlayerSummaryComponent} from './player-summary.component';
import {CourtVisualizationComponent} from './court-visualization/court-visualization.component';
import {routing} from 'app/player-summary/player-summary.routing';
import {MatToolbarModule} from '@angular/material/toolbar';
import {MatCardModule} from '@angular/material/card';
import {FlexModule} from '@angular/flex-layout';
import {MatListModule} from '@angular/material/list';
import {MatRadioModule} from '@angular/material/radio';
import {MatIconModule} from '@angular/material/icon';
import {MatButtonModule} from '@angular/material/button';
import {MatSelectModule} from '@angular/material/select';
import {MatOptionModule} from '@angular/material/core';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTooltipModule} from '@angular/material/tooltip';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {PlayersService} from 'app/_services/players.service';
import {PlayerSummaryService} from './player-summary.service';


@NgModule({
  declarations: [
    PlayerSummaryComponent,
    CourtVisualizationComponent
  ],
  imports: [
    CommonModule,
    routing,
    MatToolbarModule,
    MatCardModule,
    FlexModule,
    MatListModule,
    MatRadioModule,
    MatIconModule,
    MatButtonModule,
    MatSelectModule,
    MatOptionModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    FormsModule,
    ReactiveFormsModule
  ],
  providers: [PlayersService, PlayerSummaryService],
  bootstrap: [PlayerSummaryComponent],
})
export class PlayerSummaryModule { }